"""Claude Agent SDK service wrapper with streaming support and multi-turn conversation."""

import os
import json
import asyncio
from typing import AsyncIterator, Optional, Any, Callable, Dict
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import asynccontextmanager

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
    type: str  # "text", "tool_use", "tool_result", "system", "result", "error", "thinking"
    content: str
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None
    metadata: Optional[dict] = None


@dataclass
class ConversationContext:
    """Context for a conversation session."""
    session_id: str
    workspace_path: str
    client: Optional[ClaudeSDKClient] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    is_connected: bool = False
    
    def touch(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
        self.message_count += 1


class ClaudeService:
    """Service for interacting with Claude SDK with multi-turn conversation support."""
    
    # Default tools available for Claude
    DEFAULT_TOOLS = [
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
    
    def __init__(
        self,
        workspace_path: Optional[str] = None,
        allowed_tools: Optional[list[str]] = None,
        session_id: Optional[str] = None,
    ):
        """Initialize Claude service.
        
        Args:
            workspace_path: Working directory for Claude operations
            allowed_tools: List of tools to enable (default: common tools)
            session_id: Session identifier for multi-turn conversations
        """
        self.workspace_path = workspace_path
        self.allowed_tools = allowed_tools or self.DEFAULT_TOOLS.copy()
        self.session_id = session_id
        self._client: Optional[ClaudeSDKClient] = None
        self._is_connected = False
        
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
    
    async def connect(self) -> ClaudeSDKClient:
        """Connect to Claude SDK client.
        
        Returns:
            Connected ClaudeSDKClient instance
        """
        if self._client is not None and self._is_connected:
            return self._client
            
        options = self._create_options()
        self._client = ClaudeSDKClient(options=options)
        await self._client.connect()
        self._is_connected = True
        return self._client
    
    async def disconnect(self):
        """Disconnect from Claude SDK client."""
        if self._client is not None and self._is_connected:
            try:
                await self._client.disconnect()
            except RuntimeError as e:
                # Ignore cancel scope errors during cleanup
                if "cancel scope" not in str(e).lower():
                    raise
            finally:
                self._is_connected = False
    
    @asynccontextmanager
    async def connection(self):
        """Context manager for Claude client connection."""
        try:
            client = await self.connect()
            yield client
        finally:
            await self.disconnect()
    
    async def chat_stream(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        on_message: Optional[Callable[[ChatMessage], None]] = None,
    ) -> AsyncIterator[ChatMessage]:
        """Send a message and stream responses with multi-turn conversation support.
        
        Args:
            prompt: User message to send
            session_id: Session ID for multi-turn conversation (uses instance session_id if not provided)
            on_message: Optional callback for each message
            
        Yields:
            ChatMessage objects for each response chunk
        """
        # Use provided session_id or fall back to instance session_id
        effective_session_id = session_id or self.session_id
        
        client = await self.connect()
        generator_closed = False
        
        try:
            # Send query with session_id for multi-turn conversation support
            if effective_session_id:
                await client.query(prompt, session_id=effective_session_id)
            else:
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
                    await self.disconnect()
                except RuntimeError as e:
                    # Ignore cancel scope errors that occur during cleanup
                    if "cancel scope" not in str(e).lower():
                        raise
    
    async def chat(
        self,
        prompt: str,
        session_id: Optional[str] = None,
    ) -> list[ChatMessage]:
        """Send a message and get all responses.
        
        Args:
            prompt: User message to send
            session_id: Session ID for multi-turn conversation
            
        Returns:
            List of ChatMessage objects
        """
        messages = []
        async for msg in self.chat_stream(prompt, session_id=session_id):
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
    """Manager for Claude clients across multiple sessions with connection reuse."""
    
    # Session timeout in seconds (30 minutes)
    SESSION_TIMEOUT = 1800
    
    def __init__(self):
        self._contexts: Dict[str, ConversationContext] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        
    def _get_lock(self, session_id: str) -> asyncio.Lock:
        """Get or create lock for session."""
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()
        return self._locks[session_id]
    
    async def get_or_create_context(
        self,
        session_id: str,
        workspace_path: str,
    ) -> ConversationContext:
        """Get existing context or create a new one.
        
        Args:
            session_id: Session identifier
            workspace_path: Working directory path
            
        Returns:
            ConversationContext for the session
        """
        async with self._get_lock(session_id):
            if session_id in self._contexts:
                context = self._contexts[session_id]
                context.touch()
                return context
                    
            # Create new context
            context = ConversationContext(
                session_id=session_id,
                workspace_path=workspace_path,
            )
            self._contexts[session_id] = context
            return context
    
    async def get_service(
        self,
        session_id: str,
        workspace_path: str,
    ) -> ClaudeService:
        """Get Claude service for a session with multi-turn support.
        
        Args:
            session_id: Session identifier
            workspace_path: Working directory path
            
        Returns:
            ClaudeService instance configured for the session
        """
        context = await self.get_or_create_context(session_id, workspace_path)
        return ClaudeService(
            workspace_path=workspace_path,
            session_id=session_id,  # Pass session_id for multi-turn support
        )
    
    async def close_session(self, session_id: str):
        """Close and cleanup session client."""
        async with self._get_lock(session_id):
            if session_id in self._contexts:
                context = self._contexts.pop(session_id)
                if context.client is not None and context.is_connected:
                    try:
                        await context.client.disconnect()
                    except Exception:
                        pass  # Ignore errors during cleanup
                    
            if session_id in self._locks:
                del self._locks[session_id]
    
    async def close_all(self):
        """Close all session clients."""
        for session_id in list(self._contexts.keys()):
            await self.close_session(session_id)
    
    async def cleanup_stale_sessions(self):
        """Cleanup sessions that have been inactive for too long."""
        now = datetime.now()
        stale_sessions = []
        
        for session_id, context in self._contexts.items():
            elapsed = (now - context.last_activity).total_seconds()
            if elapsed > self.SESSION_TIMEOUT:
                stale_sessions.append(session_id)
        
        for session_id in stale_sessions:
            await self.close_session(session_id)
    
    async def start_cleanup_task(self):
        """Start background task for cleaning up stale sessions."""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(300)  # Check every 5 minutes
                await self.cleanup_stale_sessions()
        
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    def get_session_stats(self, session_id: str) -> Optional[dict]:
        """Get statistics for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict with session statistics or None if not found
        """
        if session_id not in self._contexts:
            return None
            
        context = self._contexts[session_id]
        return {
            "session_id": context.session_id,
            "workspace_path": context.workspace_path,
            "created_at": context.created_at.isoformat(),
            "last_activity": context.last_activity.isoformat(),
            "message_count": context.message_count,
            "is_connected": context.is_connected,
        }


# Global session manager instance
session_claude_manager = SessionClaudeManager()
