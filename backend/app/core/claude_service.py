"""
Sandbox executor service for Claude Code execution.

This service provides task execution in isolated Docker containers.
All Claude-related configuration is handled inside the container.
"""

import json
import asyncio
import logging
from typing import AsyncIterator, Optional, Callable, Dict, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.config import ExecutorConfig

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Message types for SSE transmission."""
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
    INTERRUPTED = "interrupted"


@dataclass
class ChatMessage:
    """Chat message for SSE transmission."""
    type: str
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


@dataclass
class ConversationContext:
    """Context for a conversation session."""
    session_id: str
    workspace_path: str
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    
    def touch(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
        self.message_count += 1
    
    def age_seconds(self) -> float:
        """Get age of last activity in seconds."""
        return (datetime.now() - self.last_activity).total_seconds()


class SandboxService:
    """
    Service for executing tasks in sandbox containers.
    
    All execution happens in isolated Docker containers.
    Configuration is handled inside the container.
    """
    
    def __init__(
        self,
        workspace_path: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        """Initialize sandbox service.
        
        Args:
            workspace_path: Working directory path (mounted to container)
            session_id: Session identifier
        """
        self.workspace_path = workspace_path
        self.session_id = session_id
        self._executor = None
    
    def _get_executor(self):
        """Get sandbox executor instance."""
        if self._executor is None:
            from app.core.executor import get_sandbox_executor
            self._executor = get_sandbox_executor()
        return self._executor
    
    async def chat_stream(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        on_message: Optional[Callable[[ChatMessage], None]] = None,
    ) -> AsyncIterator[ChatMessage]:
        """Send a message and stream responses from sandbox container.
        
        Args:
            prompt: User message to send
            session_id: Session ID for multi-turn conversation
            on_message: Optional callback for each message
            
        Yields:
            ChatMessage objects for each response chunk
        """
        effective_session_id = session_id or self.session_id
        executor = self._get_executor()
        
        try:
            async for event in executor.execute_stream(
                session_id=effective_session_id,
                workspace_path=self.workspace_path,
                prompt=prompt,
            ):
                chat_msg = self._event_to_chat_message(event)
                if chat_msg:
                    if on_message:
                        on_message(chat_msg)
                    yield chat_msg
                    
        except Exception as e:
            logger.error(f"Error during sandbox chat stream: {e}", exc_info=True)
            error_msg = ChatMessage(
                type=MessageType.ERROR.value,
                content=str(e),
            )
            if on_message:
                on_message(error_msg)
            yield error_msg
    
    def _event_to_chat_message(self, event: Dict) -> Optional[ChatMessage]:
        """Convert executor event to ChatMessage."""
        event_type = event.get("type", "")
        content = event.get("content", "")
        
        type_mapping = {
            "text": MessageType.TEXT.value,
            "text_delta": MessageType.TEXT_DELTA.value,
            "tool_use": MessageType.TOOL_USE.value,
            "tool_result": MessageType.TOOL_RESULT.value,
            "system": MessageType.SYSTEM.value,
            "result": MessageType.RESULT.value,
            "error": MessageType.ERROR.value,
            "thinking": MessageType.THINKING.value,
            "connected": MessageType.CONNECTED.value,
            "response_complete": MessageType.RESPONSE_COMPLETE.value,
            "interrupted": MessageType.INTERRUPTED.value,
        }
        
        msg_type = type_mapping.get(event_type, event_type)
        
        return ChatMessage(
            type=msg_type,
            content=content,
            tool_name=event.get("tool_name"),
            tool_input=event.get("tool_input"),
            metadata=event.get("metadata"),
        )
    
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
        """Interrupt the current operation.
        
        Returns:
            True if interrupt was sent successfully
        """
        executor = self._get_executor()
        return await executor.cancel(self.session_id)
    
    async def cleanup(self) -> bool:
        """Cleanup resources for this session.
        
        Returns:
            True if cleanup was successful
        """
        executor = self._get_executor()
        return await executor.cleanup(self.session_id)


class SessionManager:
    """
    Manager for sandbox sessions.
    
    Handles session lifecycle and cleanup.
    """
    
    def __init__(self, session_timeout: Optional[int] = None):
        """Initialize session manager.
        
        Args:
            session_timeout: Session timeout in seconds
        """
        self._contexts: Dict[str, ConversationContext] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._session_timeout = session_timeout or 1800  # Default 30 minutes
        
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
        """Get existing context or create a new one."""
        async with self._get_lock(session_id):
            if session_id in self._contexts:
                context = self._contexts[session_id]
                context.touch()
                return context
                    
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
    ) -> SandboxService:
        """Get sandbox service for a session.
        
        Args:
            session_id: Session identifier
            workspace_path: Working directory path
            
        Returns:
            SandboxService instance configured for the session
        """
        await self.get_or_create_context(session_id, workspace_path)
        return SandboxService(
            workspace_path=workspace_path,
            session_id=session_id,
        )
    
    async def close_session(self, session_id: str):
        """Close and cleanup session."""
        async with self._get_lock(session_id):
            if session_id in self._contexts:
                self._contexts.pop(session_id)
                
                # Cleanup container
                try:
                    from app.core.executor import get_sandbox_executor
                    executor = get_sandbox_executor()
                    await executor.cleanup(session_id)
                except Exception as e:
                    logger.warning(f"Error cleaning up container for session {session_id}: {e}")
                
                logger.info(f"Closed session: {session_id}")
                    
            if session_id in self._locks:
                del self._locks[session_id]
    
    async def close_all(self):
        """Close all sessions."""
        session_ids = list(self._contexts.keys())
        for session_id in session_ids:
            await self.close_session(session_id)
        logger.info(f"Closed all {len(session_ids)} sessions")
    
    async def cleanup_stale_sessions(self):
        """Cleanup sessions that have been inactive for too long."""
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
        """Get statistics for a session."""
        if session_id not in self._contexts:
            return None
            
        context = self._contexts[session_id]
        return {
            "session_id": context.session_id,
            "workspace_path": context.workspace_path,
            "created_at": context.created_at.isoformat(),
            "last_activity": context.last_activity.isoformat(),
            "message_count": context.message_count,
            "age_seconds": context.age_seconds(),
        }
    
    def get_all_stats(self) -> Dict[str, dict]:
        """Get statistics for all sessions."""
        return {
            session_id: self.get_session_stats(session_id)
            for session_id in self._contexts.keys()
        }


# Global session manager instance
session_manager = SessionManager()

# Backward compatibility aliases
ClaudeService = SandboxService
session_claude_manager = session_manager
