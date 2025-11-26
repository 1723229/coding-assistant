"""Claude Agent SDK service wrapper with streaming support."""

import os
import json
import asyncio
from typing import AsyncIterator, Optional, Any, Callable
from dataclasses import dataclass

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    AssistantMessage,
    UserMessage,
    SystemMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ThinkingBlock,
)

from ..config import get_settings

settings = get_settings()


@dataclass
class ChatMessage:
    """Simplified chat message for WebSocket transmission."""
    type: str  # "text", "tool_use", "tool_result", "system", "result", "error"
    content: str
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None
    metadata: Optional[dict] = None


class ClaudeService:
    """Service for interacting with Claude SDK."""
    
    def __init__(
        self,
        workspace_path: Optional[str] = None,
        allowed_tools: Optional[list[str]] = None,
    ):
        """Initialize Claude service.
        
        Args:
            workspace_path: Working directory for Claude operations
            allowed_tools: List of tools to enable (default: common tools)
        """
        self.workspace_path = workspace_path
        self.allowed_tools = allowed_tools or [
            "Read",
            "Write", 
            "Edit",
            "MultiEdit",
            "Bash",
            "Glob",
            "Grep",
            "LS",
            "TodoRead",
            "TodoWrite",
        ]
        self._client: Optional[ClaudeSDKClient] = None
        
    def _create_options(self) -> ClaudeAgentOptions:
        """Create Claude agent options."""
        options = ClaudeAgentOptions(
            allowed_tools=self.allowed_tools,
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
                "append": "You are helping the user with their coding tasks in a web-based IDE environment.",
            },
            permission_mode="acceptEdits",  # Auto-accept file edits for web environment
            cwd=self.workspace_path,
            include_partial_messages=True,  # Enable streaming partial messages
        )
        return options
    
    async def create_client(self) -> ClaudeSDKClient:
        """Create and connect a new Claude client."""
        options = self._create_options()
        client = ClaudeSDKClient(options=options)
        await client.connect()
        return client
    
    async def chat_stream(
        self,
        prompt: str,
        on_message: Optional[Callable[[ChatMessage], None]] = None,
    ) -> AsyncIterator[ChatMessage]:
        """Send a message and stream responses.
        
        Args:
            prompt: User message to send
            on_message: Optional callback for each message
            
        Yields:
            ChatMessage objects for each response chunk
        """
        client = await self.create_client()
        generator_closed = False
        
        try:
            await client.query(prompt)
            
            async for msg in client.receive_response():
                chat_messages = self._parse_message(msg)
                for chat_msg in chat_messages:
                    if on_message:
                        on_message(chat_msg)
                    yield chat_msg
                    
        except GeneratorExit:
            # Client disconnected - mark as closed to avoid disconnect in finally
            generator_closed = True
            raise
                    
        except Exception as e:
            error_msg = ChatMessage(
                type="error",
                content=str(e),
            )
            if on_message:
                on_message(error_msg)
            yield error_msg
            
        finally:
            # Only disconnect if generator wasn't closed prematurely
            # When GeneratorExit occurs, the client's internal task group may be
            # in a different context, causing "cancel scope in different task" errors
            if not generator_closed:
                try:
                    await client.disconnect()
                except RuntimeError as e:
                    # Ignore cancel scope errors that occur during cleanup
                    if "cancel scope" not in str(e).lower():
                        raise
    
    async def chat(self, prompt: str) -> list[ChatMessage]:
        """Send a message and get all responses.
        
        Args:
            prompt: User message to send
            
        Returns:
            List of ChatMessage objects
        """
        messages = []
        async for msg in self.chat_stream(prompt):
            messages.append(msg)
        return messages
    
    def _parse_message(self, msg: Any) -> list[ChatMessage]:
        """Parse SDK message into ChatMessage objects."""
        messages = []
        
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    messages.append(ChatMessage(
                        type="text",
                        content=block.text,
                    ))
                elif isinstance(block, ThinkingBlock):
                    messages.append(ChatMessage(
                        type="thinking",
                        content=block.thinking,
                    ))
                elif isinstance(block, ToolUseBlock):
                    messages.append(ChatMessage(
                        type="tool_use",
                        content=f"Using tool: {block.name}",
                        tool_name=block.name,
                        tool_input=block.input,
                        metadata={"tool_use_id": block.id},
                    ))
                    
        elif isinstance(msg, UserMessage):
            content_list = msg.content if isinstance(msg.content, list) else []
            for block in content_list:
                if isinstance(block, ToolResultBlock):
                    content = block.content if isinstance(block.content, str) else json.dumps(block.content) if block.content else ""
                    messages.append(ChatMessage(
                        type="tool_result",
                        content=content[:500] + "..." if len(content) > 500 else content,
                        metadata={
                            "tool_use_id": block.tool_use_id,
                            "is_error": block.is_error,
                        },
                    ))
                    
        elif isinstance(msg, SystemMessage):
            messages.append(ChatMessage(
                type="system",
                content=json.dumps(msg.data) if msg.data else msg.subtype,
                metadata={"subtype": msg.subtype},
            ))
            
        elif isinstance(msg, ResultMessage):
            messages.append(ChatMessage(
                type="result",
                content=msg.result or "Task completed",
                metadata={
                    "duration_ms": msg.duration_ms,
                    "num_turns": msg.num_turns,
                    "session_id": msg.session_id,
                    "total_cost_usd": msg.total_cost_usd,
                    "is_error": msg.is_error,
                },
            ))
        
        # Handle any other message types as dict
        elif hasattr(msg, '__dict__'):
            # Try to extract useful info from unknown message types
            msg_dict = msg.__dict__ if hasattr(msg, '__dict__') else {}
            if 'event' in msg_dict:
                # This might be a stream event
                event_data = msg_dict.get('event', {})
                if isinstance(event_data, dict) and event_data.get("type") == "content_block_delta":
                    delta = event_data.get("delta", {})
                    if delta.get("type") == "text_delta":
                        messages.append(ChatMessage(
                            type="text_delta",
                            content=delta.get("text", ""),
                            metadata={"streaming": True},
                        ))
        
        return messages


class SessionClaudeManager:
    """Manager for Claude clients across multiple sessions."""
    
    def __init__(self):
        self._clients: dict[str, ClaudeSDKClient] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        
    def _get_lock(self, session_id: str) -> asyncio.Lock:
        """Get or create lock for session."""
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()
        return self._locks[session_id]
    
    async def get_service(
        self,
        session_id: str,
        workspace_path: str,
    ) -> ClaudeService:
        """Get Claude service for a session.
        
        Args:
            session_id: Session identifier
            workspace_path: Working directory path
            
        Returns:
            ClaudeService instance configured for the session
        """
        return ClaudeService(workspace_path=workspace_path)
    
    async def close_session(self, session_id: str):
        """Close and cleanup session client."""
        if session_id in self._clients:
            client = self._clients.pop(session_id)
            await client.disconnect()
            
        if session_id in self._locks:
            del self._locks[session_id]
    
    async def close_all(self):
        """Close all session clients."""
        for session_id in list(self._clients.keys()):
            await self.close_session(session_id)


# Global session manager instance
session_claude_manager = SessionClaudeManager()
