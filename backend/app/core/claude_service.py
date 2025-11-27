"""
Claude Agent SDK service wrapper with streaming support and multi-turn conversation.

This service provides a clean abstraction over the Claude Agent SDK for:
- Multi-turn conversations with session management
- Streaming responses via WebSocket
- Tool use tracking and result handling
- Graceful error handling and cleanup

Reference: https://platform.claude.com/docs/en/agent-sdk/python
"""

import os
import json
import asyncio
import logging
from typing import AsyncIterator, Optional, Any, Callable, Dict, List
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import asynccontextmanager
from enum import Enum

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

from app.config import ClaudeConfig

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Chat message types for WebSocket transmission."""
    TEXT = "text"
    TEXT_DELTA = "text_delta"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    SYSTEM = "system"
    RESULT = "result"
    ERROR = "error"
    THINKING = "thinking"
    CONNECTED = "connected"
    RESPONSE_COMPLETE = "response_complete"


@dataclass
class ChatMessage:
    """Simplified chat message for WebSocket transmission."""
    type: str  # MessageType value
    content: str
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None
    metadata: Optional[dict] = None
    timestamp: Optional[str] = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type,
            "content": self.content,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

PUPPETEER_TOOLS = [
    "mcp__puppeteer__puppeteer_navigate",
    "mcp__puppeteer__puppeteer_screenshot",
    "mcp__puppeteer__puppeteer_click",
    "mcp__puppeteer__puppeteer_fill",
    "mcp__puppeteer__puppeteer_select",
    "mcp__puppeteer__puppeteer_hover",
    "mcp__puppeteer__puppeteer_evaluate",
]

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
    
    def age_seconds(self) -> float:
        """Get age of last activity in seconds."""
        return (datetime.now() - self.last_activity).total_seconds()


class ClaudeService:
    """
    Service for interacting with Claude SDK with multi-turn conversation support.
    
    This service uses ClaudeSDKClient for session continuity, which maintains
    conversation context across multiple exchanges. This is essential for:
    - Follow-up questions that build on previous responses
    - Interactive coding sessions where Claude remembers file changes
    - Response-driven logic where next actions depend on Claude's response
    
    Reference: https://platform.claude.com/docs/en/agent-sdk/python
    """
    
    def __init__(
        self,
        workspace_path: Optional[str] = None,
        allowed_tools: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        permission_mode: Optional[str] = None,
        system_prompt: Optional[dict] = None,
    ):
        """Initialize Claude service.
        
        Args:
            workspace_path: Working directory for Claude operations
            allowed_tools: List of tools to enable (default: common tools)
            session_id: Session identifier for multi-turn conversations
            permission_mode: Permission mode (acceptEdits, bypassPermissions, etc.)
            system_prompt: Custom system prompt configuration
        """
        self.workspace_path = workspace_path
        BUILTIN_TOOLS = allowed_tools or ClaudeConfig.DEFAULT_TOOLS.copy()
        self.allowed_tools = [
            *BUILTIN_TOOLS,
            *PUPPETEER_TOOLS,
        ]
        self.session_id = session_id
        self.permission_mode = permission_mode or ClaudeConfig.PERMISSION_MODE
        self.system_prompt = system_prompt
        self._client: Optional[ClaudeSDKClient] = None
        self._is_connected = False
        
    def _create_options(self) -> ClaudeAgentOptions:
        """Create Claude agent options with proper configuration."""
        # Build system prompt
        if self.system_prompt:
            prompt_config = self.system_prompt
        else:
            prompt_config = {
                "type": "preset",
                "preset": "claude_code",
                "append": "You are helping the user with their coding tasks in a web-based IDE environment.",
            }
        
        options = ClaudeAgentOptions(
            allowed_tools=self.allowed_tools,
            system_prompt=prompt_config,
            permission_mode=self.permission_mode,
            cwd=self.workspace_path,
            include_partial_messages=True,  # Enable streaming partial messages
            model=ClaudeConfig.MODEL,  # Use configured model
            mcp_servers={
                "puppeteer": {"command": "npx", "args": ["puppeteer-mcp-server"]}
            },
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
        logger.info(f"Connected to Claude SDK for session: {self.session_id}")
        return self._client
    
    async def disconnect(self):
        """Disconnect from Claude SDK client with proper cleanup."""
        if self._client is not None and self._is_connected:
            try:
                await self._client.disconnect()
                logger.info(f"Disconnected from Claude SDK for session: {self.session_id}")
            except RuntimeError as e:
                # Ignore cancel scope errors during cleanup
                if "cancel scope" not in str(e).lower():
                    logger.warning(f"Error during disconnect: {e}")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self._is_connected = False
                self._client = None
    
    @asynccontextmanager
    async def connection(self):
        """Context manager for Claude client connection with automatic cleanup."""
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
        
        This method uses ClaudeSDKClient.query() with session_id to maintain
        conversation context. Each call with the same session_id will remember
        previous messages in the conversation.
        
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
            # The session_id parameter enables conversation continuity
            if effective_session_id:
                await client.query(prompt, session_id=effective_session_id)
                logger.debug(f"Sent query with session_id: {effective_session_id}")
            else:
                await client.query(prompt)
                logger.debug("Sent query without session_id")
            
            # Process responses using receive_response() which yields until ResultMessage
            async for msg in client.receive_response():
                chat_messages = self._parse_message(msg)
                for chat_msg in chat_messages:
                    if on_message:
                        on_message(chat_msg)
                    yield chat_msg
                    
        except GeneratorExit:
            # Client disconnected - mark as closed to avoid disconnect in finally
            generator_closed = True
            logger.debug("Generator closed by client")
            raise
                    
        except Exception as e:
            logger.error(f"Error during chat stream: {e}", exc_info=True)
            error_msg = ChatMessage(
                type=MessageType.ERROR.value,
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
                        logger.warning(f"Error during cleanup: {e}")
    
    async def chat(
        self,
        prompt: str,
        session_id: Optional[str] = None,
    ) -> List[ChatMessage]:
        """Send a message and get all responses (non-streaming).
        
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
    
    async def interrupt(self) -> bool:
        """Interrupt the current Claude operation.
        
        Returns:
            True if interrupt was sent successfully
        """
        if self._client is not None and self._is_connected:
            try:
                await self._client.interrupt()
                logger.info(f"Sent interrupt for session: {self.session_id}")
                return True
            except Exception as e:
                logger.warning(f"Error during interrupt: {e}")
        return False
    
    def _parse_message(self, msg: Any) -> List[ChatMessage]:
        """Parse SDK message into ChatMessage objects.
        
        Handles all message types from the Claude SDK:
        - AssistantMessage: Text, tool use, thinking blocks
        - UserMessage: Tool results
        - SystemMessage: System events
        - ResultMessage: Final result with metadata
        """
        messages = []
        
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    messages.append(ChatMessage(
                        type=MessageType.TEXT.value,
                        content=block.text,
                    ))
                elif isinstance(block, ThinkingBlock):
                    messages.append(ChatMessage(
                        type=MessageType.THINKING.value,
                        content=block.thinking,
                    ))
                elif isinstance(block, ToolUseBlock):
                    messages.append(ChatMessage(
                        type=MessageType.TOOL_USE.value,
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
                    # Truncate long tool results for WebSocket transmission
                    max_length = 500
                    if len(content) > max_length:
                        content = content[:max_length] + "..."
                    messages.append(ChatMessage(
                        type=MessageType.TOOL_RESULT.value,
                        content=content,
                        metadata={
                            "tool_use_id": block.tool_use_id,
                            "is_error": block.is_error,
                        },
                    ))
                    
        elif isinstance(msg, SystemMessage):
            messages.append(ChatMessage(
                type=MessageType.SYSTEM.value,
                content=json.dumps(msg.data) if msg.data else msg.subtype,
                metadata={"subtype": msg.subtype},
            ))
            
        elif isinstance(msg, ResultMessage):
            messages.append(ChatMessage(
                type=MessageType.RESULT.value,
                content=msg.result or "Task completed",
                metadata={
                    "duration_ms": msg.duration_ms,
                    "num_turns": msg.num_turns,
                    "session_id": msg.session_id,
                    "total_cost_usd": msg.total_cost_usd,
                    "is_error": msg.is_error,
                },
            ))
        
        # Handle any other message types with event data
        elif hasattr(msg, '__dict__'):
            msg_dict = msg.__dict__ if hasattr(msg, '__dict__') else {}
            if 'event' in msg_dict:
                event_data = msg_dict.get('event', {})
                if isinstance(event_data, dict) and event_data.get("type") == "content_block_delta":
                    delta = event_data.get("delta", {})
                    if delta.get("type") == "text_delta":
                        messages.append(ChatMessage(
                            type=MessageType.TEXT_DELTA.value,
                            content=delta.get("text", ""),
                            metadata={"streaming": True},
                        ))
        
        return messages


class SessionClaudeManager:
    """
    Manager for Claude clients across multiple sessions with connection reuse.
    
    This manager handles:
    - Creating and caching ClaudeService instances per session
    - Automatic cleanup of stale sessions
    - Thread-safe session access with asyncio locks
    """
    
    def __init__(self, session_timeout: Optional[int] = None):
        """Initialize session manager.
        
        Args:
            session_timeout: Session timeout in seconds (default from config)
        """
        self._contexts: Dict[str, ConversationContext] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._session_timeout = session_timeout or ClaudeConfig.SESSION_TIMEOUT
        
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
            logger.info(f"Created new context for session: {session_id}")
            return context
    
    async def get_service(
        self,
        session_id: str,
        workspace_path: str,
        allowed_tools: Optional[List[str]] = None,
    ) -> ClaudeService:
        """Get Claude service for a session with multi-turn support.
        
        Args:
            session_id: Session identifier
            workspace_path: Working directory path
            allowed_tools: Optional list of allowed tools
            
        Returns:
            ClaudeService instance configured for the session
        """
        context = await self.get_or_create_context(session_id, workspace_path)
        return ClaudeService(
            workspace_path=workspace_path,
            session_id=session_id,
            allowed_tools=allowed_tools,
        )
    
    async def close_session(self, session_id: str):
        """Close and cleanup session client."""
        async with self._get_lock(session_id):
            if session_id in self._contexts:
                context = self._contexts.pop(session_id)
                if context.client is not None and context.is_connected:
                    try:
                        await context.client.disconnect()
                    except Exception as e:
                        logger.warning(f"Error closing session {session_id}: {e}")
                logger.info(f"Closed session: {session_id}")
                    
            if session_id in self._locks:
                del self._locks[session_id]
    
    async def close_all(self):
        """Close all session clients."""
        session_ids = list(self._contexts.keys())
        for session_id in session_ids:
            await self.close_session(session_id)
        logger.info(f"Closed all {len(session_ids)} sessions")
    
    async def cleanup_stale_sessions(self):
        """Cleanup sessions that have been inactive for too long."""
        now = datetime.now()
        stale_sessions = []
        
        for session_id, context in self._contexts.items():
            if context.age_seconds() > self._session_timeout:
                stale_sessions.append(session_id)
        
        for session_id in stale_sessions:
            await self.close_session(session_id)
            logger.info(f"Cleaned up stale session: {session_id}")
        
        if stale_sessions:
            logger.info(f"Cleaned up {len(stale_sessions)} stale sessions")
    
    async def start_cleanup_task(self):
        """Start background task for cleaning up stale sessions."""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(300)  # Check every 5 minutes
                try:
                    await self.cleanup_stale_sessions()
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")
        
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(cleanup_loop())
            logger.info("Started session cleanup task")
    
    async def stop_cleanup_task(self):
        """Stop the background cleanup task."""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Stopped session cleanup task")
    
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
            "age_seconds": context.age_seconds(),
        }
    
    def get_all_stats(self) -> Dict[str, dict]:
        """Get statistics for all sessions."""
        return {
            session_id: self.get_session_stats(session_id)
            for session_id in self._contexts.keys()
        }


# Global session manager instance
session_claude_manager = SessionClaudeManager()
