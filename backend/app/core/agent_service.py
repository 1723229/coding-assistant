# -*- coding: utf-8 -*-
"""
Simple Agent Service for Claude Code SDK integration.

This service provides direct local execution of Claude Code tasks,
supporting streaming and non-streaming chat with multi-turn conversation.

No MCP servers, no Docker containers - just direct interaction.
"""

import asyncio
import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator, List

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

logger = logging.getLogger(__name__)

# Default workspace root - use user home directory
def _get_default_workspace_root() -> str:
    """Get default workspace root directory: {user_home}/workspace"""
    user_home = os.path.expanduser("~")
    return os.path.join(user_home, "workspace")

DEFAULT_WORKSPACE_ROOT = _get_default_workspace_root()

# Default tools for Claude Code (no MCP tools)
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
    "WebFetch",
]

# Default permission mode
DEFAULT_PERMISSION_MODE = "bypassPermissions"


@dataclass
class AgentSession:
    """Agent session data."""
    session_id: str
    client: ClaudeSDKClient
    workspace_path: str
    created_at: datetime = field(default_factory=datetime.now)
    is_connected: bool = False
    is_cancelled: bool = False


@dataclass
class ChatMessage:
    """Chat message for response."""
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


class AgentService:
    """
    Simple Agent Service for Claude Code SDK.

    Provides direct local execution without MCP or Docker.
    Supports streaming and non-streaming chat with multi-turn conversation.
    """

    _instance: Optional['AgentService'] = None

    def __new__(cls):
        """Singleton pattern for global service instance."""
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._sessions: Dict[str, AgentSession] = {}
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize service (only runs once due to singleton)."""
        if self._initialized:
            return
        self._initialized = True
        self._setup_environment()
        logger.info("AgentService initialized")

    def _setup_environment(self):
        """Setup environment variables for Claude SDK."""
        # Try to load from ExecutorConfig if available
        try:
            from app.config import ExecutorConfig
            if ExecutorConfig.ANTHROPIC_API_KEY:
                os.environ["ANTHROPIC_API_KEY"] = ExecutorConfig.ANTHROPIC_API_KEY
            if ExecutorConfig.ANTHROPIC_BASE_URL:
                os.environ["ANTHROPIC_BASE_URL"] = ExecutorConfig.ANTHROPIC_BASE_URL
            if ExecutorConfig.ANTHROPIC_MODEL:
                os.environ["ANTHROPIC_MODEL"] = ExecutorConfig.ANTHROPIC_MODEL
            self._permission_mode = DEFAULT_PERMISSION_MODE
            
            # Log environment variables for debugging
            logger.info(f"Environment configured:")
            logger.info(f"  ANTHROPIC_API_KEY: {os.environ.get('ANTHROPIC_API_KEY', '')[:20]}...")
            logger.info(f"  ANTHROPIC_BASE_URL: {os.environ.get('ANTHROPIC_BASE_URL', '')}")
            logger.info(f"  ANTHROPIC_MODEL: {os.environ.get('ANTHROPIC_MODEL', '')}")
        except ImportError:
            self._permission_mode = DEFAULT_PERMISSION_MODE
            logger.warning("ExecutorConfig not available, using environment variables")

        # Disable experimental betas for API proxy compatibility
        os.environ.setdefault("CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS", "1")

    def _get_workspace_path(self, session_id: str) -> str:
        """
        Get workspace path for a session.

        Workspace path is always: {user_home}/workspace/{session_id}

        Args:
            session_id: Session identifier

        Returns:
            Absolute workspace path (created if not exists)
        """
        path = os.path.join(DEFAULT_WORKSPACE_ROOT, session_id)

        # Ensure directory exists
        is_new_workspace = not os.path.exists(path)
        if is_new_workspace:
            os.makedirs(path, exist_ok=True)
            logger.info(f"Created workspace directory: {path}")

        # Copy .claude directory from current project to workspace if it exists
        self._copy_claude_config(path)

        return path

    def _copy_claude_config(self, workspace_path: str) -> None:
        """
        Copy .claude directory from project root to workspace.

        The project root is determined by going up from this file's location
        (backend/app/core/agent_service.py) to find the .claude directory.

        Args:
            workspace_path: Target workspace path
        """
        # This file is at: backend/app/core/agent_service.py
        # Project root .claude is at: ../../.. (3 levels up)
        current_file = os.path.abspath(__file__)
        # Go up: agent_service.py -> core -> app -> backend -> project_root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))
        project_claude_dir = os.path.join(project_root, ".claude")

        if not os.path.isdir(project_claude_dir):
            logger.debug(f"No .claude directory found at project root: {project_claude_dir}")
            return

        # Target .claude directory in workspace
        target_claude_dir = os.path.join(workspace_path, ".claude")

        # Skip if already exists
        if os.path.exists(target_claude_dir):
            logger.debug(f".claude directory already exists in workspace: {target_claude_dir}")
            return

        # Copy the directory
        try:
            shutil.copytree(project_claude_dir, target_claude_dir)
            logger.info(f"Copied .claude from {project_claude_dir} to {target_claude_dir}")
        except Exception as e:
            logger.warning(f"Failed to copy .claude directory: {e}")

    def _create_options(self, workspace_path: str) -> ClaudeAgentOptions:
        """
        Create Claude agent options.

        Args:
            workspace_path: Working directory for the agent

        Returns:
            ClaudeAgentOptions configured for local execution
        """
        prompt_config = {
            "type": "preset",
            "preset": "claude_code",
            "append": "You are helping the user with their coding tasks.",
        }

        options = ClaudeAgentOptions(
            allowed_tools=DEFAULT_TOOLS.copy(),
            system_prompt=prompt_config,
            permission_mode=self._permission_mode,
            cwd=workspace_path,
            include_partial_messages=True,
            setting_sources=["project", "local", "user"],
        )

        return options

    async def _get_or_create_session(
            self,
            session_id: str,
    ) -> AgentSession:
        """
        Get existing session or create a new one.

        Multi-turn conversation support:
        - Check if existing client's internal read task is still running
        - If the read task was cancelled, create a new client
        - Same session_id maintains conversation history via Claude Code's session_id parameter

        Args:
            session_id: Unique session identifier

        Returns:
            AgentSession instance
        """
        # Get workspace path: {user_home}/workspace/{session_id}
        effective_workspace = self._get_workspace_path(session_id)

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
                                logger.warning(
                                    f"Cached client process terminated (returncode={process.returncode}) "
                                    f"for session: {session_id}"
                                )
                                need_new_client = True
                            else:
                                # Process is running, but check if read task is alive
                                if hasattr(client, '_query') and client._query:
                                    query = client._query
                                    tasks = query._tg._tasks if hasattr(query._tg, '_tasks') else set()
                                    if len(tasks) == 0:
                                        logger.warning(
                                            f"Read task was cancelled for session: {session_id}, "
                                            f"creating new client"
                                        )
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
                                        logger.warning(
                                            f"Read task was cancelled for session: {session_id}, "
                                            f"creating new client"
                                        )
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
                    except Exception as cleanup_err:
                        logger.warning(f"Error cleaning up old session: {cleanup_err}")

            except Exception as e:
                logger.warning(
                    f"Error checking client validity for session {session_id}: {e}, "
                    f"creating new client"
                )
                if session_id in self._sessions:
                    try:
                        del self._sessions[session_id]
                    except Exception:
                        pass

        # Change to workspace directory before creating client
        try:
            os.chdir(effective_workspace)
            logger.info(f"Changed to workspace directory: {effective_workspace}")
        except Exception as e:
            logger.error(f"Failed to change to workspace directory: {e}")
            raise RuntimeError(f"Cannot change to workspace directory: {effective_workspace}")

        # Create new session
        logger.info(f"Creating new Claude client for session: {session_id}")

        options = self._create_options(workspace_path=effective_workspace)

        client = ClaudeSDKClient(options=options)
        await client.connect()

        session = AgentSession(
            session_id=session_id,
            client=client,
            workspace_path=effective_workspace,
            is_connected=True,
        )

        self._sessions[session_id] = session
        logger.info(f"Created new agent session: {session_id}")
        return session

    def _parse_message(self, msg: Any) -> List[Dict[str, Any]]:
        """
        Parse SDK message into event dictionaries.

        Args:
            msg: Message from Claude SDK

        Returns:
            List of event dictionaries
        """
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
                    # Debug: log the raw tool input
                    logger.debug(f"ToolUseBlock: name={block.name}, id={block.id}, input_type={type(block.input)}, input={str(block.input)[:500]}")
                    if block.name == "Write" and (not block.input or not block.input.get("file_path")):
                        logger.warning(f"Empty or invalid Write tool input detected: {block.input}")
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
                    content = block.content if isinstance(block.content, str) else json.dumps(
                        block.content) if block.content else ""
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

    async def chat_stream(
            self,
            prompt: str,
            session_id: str,
    ) -> AsyncGenerator[ChatMessage, None]:
        """
        Execute a chat with streaming response.

        Args:
            prompt: User prompt/query
            session_id: Unique session identifier for multi-turn conversation
                       Workspace will be created at: {user_home}/workspace/{session_id}

        Yields:
            ChatMessage objects for each response chunk
        """
        try:
            # Get or create session
            session = await self._get_or_create_session(session_id=session_id)

            # Send query
            logger.info(f"Sending query for session: {session_id}, prompt length: {len(prompt)}")
            await session.client.query(prompt, session_id=session_id)
            logger.info(f"Query sent, starting to receive response for session: {session_id}")

            # Stream responses
            msg_count = 0
            async for msg in session.client.receive_response():
                msg_count += 1
                logger.debug(f"Received message #{msg_count} type: {type(msg).__name__} for session: {session_id} ,msg: {msg}")

                # Check for cancellation
                if session.is_cancelled:
                    logger.info(f"Stream cancelled for session: {session_id}")
                    yield ChatMessage(type="interrupted", content="Task cancelled")
                    break

                # Parse and yield events
                events = self._parse_message(msg)
                for event in events:
                    yield ChatMessage(
                        type=event.get("type", "unknown"),
                        content=event.get("content", ""),
                        tool_name=event.get("tool_name"),
                        tool_input=event.get("tool_input"),
                        metadata=event.get("metadata"),
                    )

        except asyncio.CancelledError:
            logger.info(f"Stream cancelled for session: {session_id}")
            yield ChatMessage(type="interrupted", content="Stream cancelled")

            # Clean up the session on cancellation
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
            yield ChatMessage(type="error", content=str(e))

            # Clean up the session on error
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

    async def chat(
            self,
            prompt: str,
            session_id: str,
    ) -> List[ChatMessage]:
        """
        Execute a chat and return all responses (non-streaming).

        Args:
            prompt: User prompt/query
            session_id: Unique session identifier for multi-turn conversation
                       Workspace will be created at: {user_home}/workspace/{session_id}

        Returns:
            List of ChatMessage objects
        """
        messages = []
        async for msg in self.chat_stream(prompt=prompt, session_id=session_id):
            messages.append(msg)
        return messages

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
        Close a session.

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
                    logger.info(f"Closed session: {session_id}")
                    return True
            except Exception as e:
                logger.warning(f"Error closing session {session_id}: {e}")

        return False

    async def close_all_sessions(self):
        """Close all sessions."""
        session_ids = list(self._sessions.keys())
        for session_id in session_ids:
            await self.close_session(session_id)
        logger.info(f"Closed {len(session_ids)} sessions")

    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all active sessions.

        Returns:
            List of session info dictionaries
        """
        return [
            {
                "session_id": session_id,
                "workspace_path": session.workspace_path,
                "created_at": session.created_at.isoformat(),
                "is_connected": session.is_connected,
            }
            for session_id, session in self._sessions.items()
        ]


# Global service instance
agent_service = AgentService()

