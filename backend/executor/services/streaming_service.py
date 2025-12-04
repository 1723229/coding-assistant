# -*- coding: utf-8 -*-
"""
Streaming agent service for SSE-based task execution.

This service provides async streaming execution of Claude Code tasks,
yielding events as they occur for real-time updates via SSE.
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime

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

from executor.config import config

logger = logging.getLogger(__name__)


@dataclass
class StreamingSession:
    """Streaming session data."""
    session_id: str
    client: ClaudeSDKClient
    workspace_path: str
    created_at: datetime = field(default_factory=datetime.now)
    is_connected: bool = False
    is_cancelled: bool = False


class StreamingAgentService:
    """
    Service for streaming Claude Code task execution.
    
    This service manages async streaming sessions and provides
    real-time event streaming via SSE.
    """
    
    _instance: Optional['StreamingAgentService'] = None
    
    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._sessions: Dict[str, StreamingSession] = {}
        return cls._instance
    
    def _create_options(
        self,
        workspace_path: str,
        allowed_tools: Optional[list] = None,
        permission_mode: Optional[str] = None,
        system_prompt: Optional[dict] = None,
        model: Optional[str] = None,
    ) -> ClaudeAgentOptions:
        """Create Claude agent options."""
        if system_prompt:
            prompt_config = system_prompt
        else:
            prompt_config = {
                "type": "preset",
                "preset": "claude_code",
                "append": "You are helping the user with their coding tasks in a sandbox environment.",
            }
        
        options = ClaudeAgentOptions(
            allowed_tools=allowed_tools or config.DEFAULT_TOOLS.copy(),
            system_prompt=prompt_config,
            permission_mode=permission_mode or config.PERMISSION_MODE,
            cwd=workspace_path,
            include_partial_messages=True,
            model=model or config.ANTHROPIC_MODEL,
        )
        return options
    
    async def _get_or_create_session(
        self,
        session_id: str,
        workspace_path: str,
        **kwargs,
    ) -> StreamingSession:
        """Get existing session or create a new one.
        
        Multi-turn conversation support:
        - Check if existing client's internal read task is still running
        - If the read task was cancelled (happens after HTTP response completes),
          we must create a new client because anyio TaskGroup cannot be restarted
        - Same session_id maintains conversation history via Claude Code's session_id parameter
        
        Note: When FastAPI StreamingResponse completes, the anyio TaskGroup's _read_messages
        task gets cancelled. Once cancelled, the entire TaskGroup's cancel scope is triggered
        and cannot be reused. We must create a new client connection.
        """
        import os
        
        # Check if session already exists
        if session_id in self._sessions:
            session = self._sessions[session_id]
            
            # Verify the cached client is still valid
            try:
                client = session.client
                client_valid = False
                need_new_client = False
                
                if hasattr(client, '_transport') and client._transport:
                    transport = client._transport
                    if hasattr(transport, '_process') and transport._process:
                        process = transport._process
                        # Check if process is still running
                        if hasattr(process, 'returncode'):
                            if process.returncode is not None:
                                logger.warning(f"Cached client process terminated (returncode={process.returncode}) for session: {session_id}")
                                need_new_client = True
                            else:
                                # Process is running, but check if read task is alive
                                if hasattr(client, '_query') and client._query:
                                    query = client._query
                                    tasks = query._tg._tasks if hasattr(query._tg, '_tasks') else set()
                                    if len(tasks) == 0:
                                        # Read task was cancelled, need new client
                                        logger.warning(f"Read task was cancelled for session: {session_id}, creating new client")
                                        need_new_client = True
                                    else:
                                        client_valid = True
                                else:
                                    client_valid = True
                        elif hasattr(process, 'poll'):
                            if process.poll() is not None:
                                logger.warning(f"Cached client process terminated for session: {session_id}")
                                need_new_client = True
                            else:
                                # Check read task
                                if hasattr(client, '_query') and client._query:
                                    query = client._query
                                    tasks = query._tg._tasks if hasattr(query._tg, '_tasks') else set()
                                    if len(tasks) == 0:
                                        logger.warning(f"Read task was cancelled for session: {session_id}, creating new client")
                                        need_new_client = True
                                    else:
                                        client_valid = True
                                else:
                                    client_valid = True
                
                if client_valid:
                    logger.info(f"Reusing existing Claude client for session: {session_id}")
                    session.is_cancelled = False
                    return session
                
                if need_new_client:
                    # Clean up old client before creating new one
                    logger.info(f"Cleaning up old client for session: {session_id}")
                    try:
                        del self._sessions[session_id]
                        # Don't disconnect - the process might be in a bad state
                        # Just let it be garbage collected
                    except Exception as cleanup_err:
                        logger.warning(f"Error cleaning up old session: {cleanup_err}")
                        
            except Exception as e:
                logger.warning(f"Error checking client validity for session {session_id}: {e}, creating new client")
                if session_id in self._sessions:
                    try:
                        del self._sessions[session_id]
                    except Exception:
                        pass
        
        # Ensure workspace directory exists
        if not os.path.exists(workspace_path):
            os.makedirs(workspace_path, exist_ok=True)
        
        # Change to workspace directory before creating client
        try:
            os.chdir(workspace_path)
        except Exception as e:
            logger.error(f"Failed to change to workspace directory: {e}")
            raise RuntimeError(f"Cannot change to workspace directory: {workspace_path}")
        
        # Create new session
        logger.info(f"Creating new Claude client for session: {session_id}")
        options = self._create_options(
            workspace_path=workspace_path,
            allowed_tools=kwargs.get("allowed_tools"),
            permission_mode=kwargs.get("permission_mode"),
            system_prompt=kwargs.get("system_prompt"),
            model=kwargs.get("model"),
        )
        
        client = ClaudeSDKClient(options=options)
        await client.connect()
        
        session = StreamingSession(
            session_id=session_id,
            client=client,
            workspace_path=workspace_path,
            is_connected=True,
        )
        
        self._sessions[session_id] = session
        logger.info(f"Created new streaming session: {session_id}")
        return session
    
    def _parse_message(self, msg: Any) -> list[Dict[str, Any]]:
        """Parse SDK message into event dictionaries."""
        events = []
        
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    events.append({
                        "type": "text",
                        "content": block.text,
                    })
                elif isinstance(block, ThinkingBlock):
                    events.append({
                        "type": "thinking",
                        "content": block.thinking,
                    })
                elif isinstance(block, ToolUseBlock):
                    events.append({
                        "type": "tool_use",
                        "content": f"Using tool: {block.name}",
                        "tool_name": block.name,
                        "tool_input": block.input,
                        "metadata": {"tool_use_id": block.id},
                    })
                    
        elif isinstance(msg, UserMessage):
            content_list = msg.content if isinstance(msg.content, list) else []
            for block in content_list:
                if isinstance(block, ToolResultBlock):
                    content = block.content if isinstance(block.content, str) else json.dumps(block.content) if block.content else ""
                    # Truncate long results
                    if len(content) > 500:
                        content = content[:500] + "..."
                    events.append({
                        "type": "tool_result",
                        "content": content,
                        "metadata": {
                            "tool_use_id": block.tool_use_id,
                            "is_error": block.is_error,
                        },
                    })
                    
        elif isinstance(msg, SystemMessage):
            events.append({
                "type": "system",
                "content": json.dumps(msg.data) if msg.data else msg.subtype,
                "metadata": {"subtype": msg.subtype},
            })
            
        elif isinstance(msg, ResultMessage):
            events.append({
                "type": "result",
                "content": msg.result or "Task completed",
                "metadata": {
                    "duration_ms": msg.duration_ms,
                    "num_turns": msg.num_turns,
                    "session_id": msg.session_id,
                    "total_cost_usd": msg.total_cost_usd,
                    "is_error": msg.is_error,
                },
            })
        
        # Handle partial message events (text deltas)
        elif hasattr(msg, '__dict__'):
            msg_dict = msg.__dict__ if hasattr(msg, '__dict__') else {}
            if 'event' in msg_dict:
                event_data = msg_dict.get('event', {})
                if isinstance(event_data, dict) and event_data.get("type") == "content_block_delta":
                    delta = event_data.get("delta", {})
                    if delta.get("type") == "text_delta":
                        events.append({
                            "type": "text_delta",
                            "content": delta.get("text", ""),
                            "metadata": {"streaming": True},
                        })
        
        return events
    
    async def execute_stream(
        self,
        task_data: Dict[str, Any],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute a task with streaming response.
        
        Args:
            task_data: Task data containing session_id, workspace_path, prompt, etc.
            
        Yields:
            Event dictionaries for SSE streaming
        """
        session_id = task_data.get("session_id", "")
        workspace_path = task_data.get("workspace_path", "/workspace")
        prompt = task_data.get("prompt", "")
        
        try:
            # Get or create session
            session = await self._get_or_create_session(
                session_id=session_id,
                workspace_path=workspace_path,
                allowed_tools=task_data.get("allowed_tools"),
                permission_mode=task_data.get("permission_mode"),
                system_prompt=task_data.get("system_prompt"),
                model=task_data.get("model"),
            )
            
            # Send query
            await session.client.query(prompt, session_id=session_id)
            
            # Stream responses
            async for msg in session.client.receive_response():
                # Check for cancellation
                if session.is_cancelled:
                    logger.info(f"Stream cancelled for session: {session_id}")
                    yield {"type": "interrupted", "message": "Task cancelled"}
                    break
                
                # Parse and yield events
                events = self._parse_message(msg)
                for event in events:
                    yield event
                    
        except asyncio.CancelledError:
            logger.info(f"Stream cancelled for session: {session_id}")
            yield {"type": "interrupted", "message": "Stream cancelled"}
            
            # When stream is cancelled, the client may be in an inconsistent state
            # (query sent but response not fully received). Clean up the session
            # to prevent issues on next request.
            if session_id in self._sessions:
                logger.info(f"Cleaning up cancelled session: {session_id}")
                try:
                    session = self._sessions.pop(session_id)
                    if session.client:
                        try:
                            await session.client.disconnect()
                        except Exception as disconnect_err:
                            logger.warning(f"Error disconnecting cancelled session: {disconnect_err}")
                except Exception as cleanup_err:
                    logger.warning(f"Error cleaning up cancelled session {session_id}: {cleanup_err}")
            
            raise
            
        except Exception as e:
            logger.exception(f"Error in streaming execution for session {session_id}")
            yield {"type": "error", "content": str(e)}
            
            # Clean up the session on error to prevent reusing a broken session
            if session_id in self._sessions:
                logger.info(f"Cleaning up failed session: {session_id}")
                try:
                    session = self._sessions.pop(session_id)
                    if session.client:
                        try:
                            await session.client.disconnect()
                        except Exception as disconnect_err:
                            logger.warning(f"Error disconnecting failed session: {disconnect_err}")
                except Exception as cleanup_err:
                    logger.warning(f"Error cleaning up session {session_id}: {cleanup_err}")
    
    def cancel_task(self, session_id: str) -> bool:
        """
        Cancel a streaming task.
        
        Args:
            session_id: Session ID to cancel
            
        Returns:
            True if cancellation was initiated
        """
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.is_cancelled = True
            
            # Try to interrupt the client
            try:
                if session.client and session.is_connected:
                    asyncio.create_task(session.client.interrupt())
                    logger.info(f"Sent interrupt for session: {session_id}")
                    return True
            except Exception as e:
                logger.warning(f"Error interrupting session {session_id}: {e}")
        
        return False
    
    async def close_session(self, session_id: str) -> bool:
        """
        Close a streaming session.
        
        Args:
            session_id: Session ID to close
            
        Returns:
            True if session was closed
        """
        if session_id in self._sessions:
            session = self._sessions.pop(session_id)
            try:
                if session.client and session.is_connected:
                    await session.client.disconnect()
                    logger.info(f"Closed streaming session: {session_id}")
                    return True
            except Exception as e:
                logger.warning(f"Error closing session {session_id}: {e}")
        
        return False
    
    async def close_all_sessions(self):
        """Close all streaming sessions."""
        session_ids = list(self._sessions.keys())
        for session_id in session_ids:
            await self.close_session(session_id)
        logger.info(f"Closed {len(session_ids)} streaming sessions")

