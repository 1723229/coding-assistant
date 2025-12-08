# -*- coding: utf-8 -*-
"""
Streaming agent service for SSE-based task execution.

This service provides async streaming execution of Claude Code tasks,
yielding events as they occur for real-time updates via SSE.

Supports MCP (Model Context Protocol) servers for extended tool capabilities.
See: https://platform.claude.com/docs/en/agent-sdk/mcp
"""

import asyncio
import json
import logging
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
from executor.config import config
from executor.services.openspec_prompt_builder import OpenSpecPromptBuilder

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
            mcp_servers: Optional[Dict[str, Any]] = None,
    ) -> ClaudeAgentOptions:
        """
        Create Claude agent options with optional MCP server support.

        Args:
            workspace_path: Working directory for the agent
            allowed_tools: List of allowed tools (defaults to config.DEFAULT_TOOLS)
            permission_mode: Permission mode for Claude Code
            system_prompt: Custom system prompt configuration
            model: Model to use (defaults to config.ANTHROPIC_MODEL)
            mcp_servers: MCP server configurations dict. Format:
                {
                    "server_name": {
                        "command": "npx",
                        "args": ["@playwright/mcp@latest"],
                        "env": {"KEY": "value"}  # optional
                    }
                }

        Returns:
            ClaudeAgentOptions configured with MCP servers if provided
        """
        if system_prompt:
            prompt_config = system_prompt
        else:
            prompt_config = {
                "type": "preset",
                "preset": "claude_code",
                "append": "You are helping the user with their coding tasks in a sandbox environment.",
            }

        # Build base options with MCP tools included by default
        base_tools = allowed_tools or config.DEFAULT_TOOLS.copy()
        
        options_kwargs = {
            "allowed_tools": base_tools,
            "system_prompt": prompt_config,
            "permission_mode": permission_mode or config.PERMISSION_MODE,
            "cwd": workspace_path,
            "include_partial_messages": True,
            "model": model or config.ANTHROPIC_MODEL,
            "setting_sources": ["project", "local", "user"],
        }

        # Add MCP servers - use default if not provided
        effective_mcp_servers = mcp_servers or config.DEFAULT_MCP_SERVERS
        if effective_mcp_servers:
            options_kwargs["mcp_servers"] = effective_mcp_servers
            logger.info(f"Configuring MCP servers: {list(effective_mcp_servers.keys())}")

            # Automatically add MCP tools to allowed_tools
            # This ensures Claude can use the MCP tools without explicit permission
            current_tools = list(options_kwargs["allowed_tools"])
            
            for server_name in effective_mcp_servers.keys():
                if server_name == "playwright":
                    # Add all Playwright MCP tools
                    for tool in config.PLAYWRIGHT_MCP_TOOLS:
                        if tool not in current_tools:
                            current_tools.append(tool)
                    logger.info(f"Added {len(config.PLAYWRIGHT_MCP_TOOLS)} Playwright MCP tools")
                else:
                    # For other MCP servers, log the prefix pattern
                    mcp_tool_prefix = f"mcp__{server_name}__"
                    logger.debug(f"MCP server '{server_name}' tools will be available with prefix: {mcp_tool_prefix}")
            
            options_kwargs["allowed_tools"] = current_tools

        options = ClaudeAgentOptions(**options_kwargs)
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
                                logger.warning(
                                    f"Cached client process terminated (returncode={process.returncode}) for session: {session_id}")
                                need_new_client = True
                            else:
                                # Process is running, but check if read task is alive
                                if hasattr(client, '_query') and client._query:
                                    query = client._query
                                    tasks = query._tg._tasks if hasattr(query._tg, '_tasks') else set()
                                    if len(tasks) == 0:
                                        # Read task was cancelled, need new client
                                        logger.warning(
                                            f"Read task was cancelled for session: {session_id}, creating new client")
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
                                            f"Read task was cancelled for session: {session_id}, creating new client")
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
            logger.info(f"Created workspace directory: {workspace_path}")

        # Change to workspace directory before creating client
        try:
            os.chdir(workspace_path)
            logger.info(f"Changed to workspace directory: {workspace_path}")
        except Exception as e:
            logger.error(f"Failed to change to workspace directory: {e}")
            raise RuntimeError(f"Cannot change to workspace directory: {workspace_path}")

        # Create new session
        logger.info(f"Creating new Claude client for session: {session_id}")

        # Ensure experimental betas are disabled for API proxy compatibility
        if config.CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS:
            os.environ.setdefault("CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS",
                                  config.CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS)

        # Get MCP servers from kwargs or load from config/workspace
        mcp_servers = kwargs.get("mcp_servers")
        if not mcp_servers:
            # Try to load MCP servers from config (env var or .mcp.json)
            mcp_servers = config.get_mcp_servers(workspace_path)
            if mcp_servers:
                logger.info(f"Loaded MCP servers from config: {list(mcp_servers.keys())}")
        # Note: If still no MCP servers, _create_options will use DEFAULT_MCP_SERVERS

        options = self._create_options(
            workspace_path=workspace_path,
            allowed_tools=kwargs.get("allowed_tools"),
            permission_mode=kwargs.get("permission_mode"),
            system_prompt=kwargs.get("system_prompt"),
            model=kwargs.get("model"),
            mcp_servers=mcp_servers,
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

    async def execute_stream(
            self,
            task_data: Dict[str, Any],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute a task with streaming response.

        Args:
            task_data: Task data containing:
                - session_id: Unique session identifier
                - workspace_path: Working directory path
                - prompt: User prompt/query
                - allowed_tools: Optional list of allowed tools
                - permission_mode: Optional permission mode
                - system_prompt: Optional custom system prompt
                - model: Optional model name
                - mcp_servers: Optional MCP server configurations dict

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
                mcp_servers=task_data.get("mcp_servers"),
            )

            # Send query
            logger.info(f"Sending query for session: {session_id}, prompt length: {len(prompt)}")
            await session.client.query(prompt, session_id=session_id)
            logger.info(f"Query sent, starting to receive response for session: {session_id}")

            # Stream responses
            logger.info(f"Starting receive_response iteration for session: {session_id}")
            msg_count = 0
            async for msg in session.client.receive_response():
                msg_count += 1
                logger.info(f"Received message #{msg_count} type: {type(msg).__name__} for session: {session_id}")
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

    async def _execute_single_query(
            self,
            session: 'StreamingSession',
            prompt: str,
            session_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行单个查询并流式返回结果

        Args:
            session: 流式会话对象
            prompt: 要执行的提示词
            session_id: 会话 ID

        Yields:
            事件字典
        """
        logger.debug(f"Query start: session={session_id}, prompt_len={len(prompt)}")
        await session.client.query(prompt, session_id=session_id)

        collected_output = []
        async for msg in session.client.receive_response():
            if session.is_cancelled:
                yield {"type": "interrupted", "message": "Task cancelled"}
                break

            events = self._parse_message(msg)
            for event in events:
                event_type = event.get("type", "unknown")
                if event_type in ["text", "text_delta", "tool_result"]:
                    collected_output.append(event.get("content", ""))
                    logger.info(event.get("content", ""))
                yield event

        # 返回收集的输出（用于 ID 提取）
        yield {"type": "_collected_output", "content": "\n".join(collected_output)}

    async def _extract_spec_id_via_list(
            self,
            session: 'StreamingSession',
            session_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行 openspec list 系统命令并提取 ID

        Args:
            session: 流式会话对象
            session_id: 会话 ID

        Yields:
            事件字典，最后一个事件包含提取的 ID
        """
        # 使用 openspec list 系统命令获取 ID
        list_prompt = OpenSpecPromptBuilder.build_list_prompt()

        yield {"type": "system", "content": "正在执行 openspec list 获取 ID..."}

        collected_output = ""
        async for event in self._execute_single_query(session, list_prompt, session_id):
            if event.get("type") == "_collected_output":
                collected_output = event.get("content", "")
            else:
                yield event

        # 从 openspec list 输出中提取 ID
        spec_id = OpenSpecPromptBuilder.extract_spec_id_from_output(collected_output)

        if spec_id:
            logger.info(f"Extracted spec ID: {spec_id} for session: {session_id}")
            yield {"type": "system", "content": f"提取到 OpenSpec ID: {spec_id}"}
            yield {"type": "_spec_id", "content": spec_id}
        else:
            logger.warning(f"Failed to extract spec ID from output for session: {session_id}")
            yield {"type": "error", "content": "无法从 openspec list 输出中提取 ID"}
            yield {"type": "_spec_id", "content": None}

    async def execute_openspec_stream(
            self,
            task_data: Dict[str, Any],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        根据 task_type 执行 OpenSpec 任务流程

        支持三种任务类型:
        - spec: 执行 proposal → 提取 ID → 自动执行 preview
        - preview: 提取 ID → 执行 preview + prompt
        - build: 提取 ID → 执行 apply → 执行 archive

        Args:
            task_data: 任务数据，包含 session_id, workspace_path, prompt, task_type 等

        Yields:
            事件字典用于 SSE 流式传输
        """
        session_id = task_data.get("session_id", "")
        workspace_path = task_data.get("workspace_path", "/workspace")
        user_prompt = task_data.get("prompt", "")
        task_type = task_data.get("task_type", "")

        try:
            # 获取或创建会话
            logger.info(f"OpenSpec {task_type} start: session={session_id}")
            
            session = await self._get_or_create_session(
                session_id=session_id,
                workspace_path=workspace_path,
                allowed_tools=task_data.get("allowed_tools"),
                permission_mode=task_data.get("permission_mode"),
                system_prompt=task_data.get("system_prompt"),
                model=task_data.get("model"),
                mcp_servers=task_data.get("mcp_servers"),
            )
            
            if task_type == "spec":
                # === SPEC 流程 ===
                yield {"type": "system", "content": "=== 开始执行 spec 流程 ==="}
                
                # 步骤1: 执行 proposal
                yield {"type": "system", "content": "步骤 1/3: 执行 proposal..."}
                proposal_prompt = OpenSpecPromptBuilder.build_proposal_prompt(user_prompt)
                async for event in self._execute_single_query(session, proposal_prompt, session_id):
                    if event.get("type") != "_collected_output":
                        yield event
                
                # 步骤2: 执行 openspec list 提取 ID
                yield {"type": "system", "content": "步骤 2/3: 获取 OpenSpec ID..."}
                spec_id = None
                async for event in self._extract_spec_id_via_list(session, session_id):
                    if event.get("type") == "_spec_id":
                        spec_id = event.get("content")
                    elif event.get("type") != "_collected_output":
                        yield event
                
                if not spec_id:
                    logger.error(f"Failed to get spec ID: session={session_id}")
                    yield {"type": "error", "content": "无法获取 OpenSpec ID，流程终止"}
                    return
                
                yield {"type": "spec_id", "content": spec_id}
                logger.info(f"Spec ID extracted: {spec_id}")
                
                # 步骤3: 自动执行 preview
                yield {"type": "system", "content": f"步骤 3/3: 执行 preview (ID: {spec_id})..."}
                preview_prompt = OpenSpecPromptBuilder.build_preview_prompt(spec_id)
                async for event in self._execute_single_query(session, preview_prompt, session_id):
                    if event.get("type") != "_collected_output":
                        yield event
                
                yield {"type": "system", "content": "=== spec 流程完成 ==="}
                yield {"type": "complete", "content": "spec 流程执行完成", "spec_id": spec_id}
                logger.info(f"OpenSpec spec completed: session={session_id}")
                
            elif task_type == "preview":
                # === PREVIEW 流程 ===
                yield {"type": "system", "content": "=== 开始执行 preview 流程 ==="}
                
                # 步骤1: 执行 openspec list 提取 ID
                yield {"type": "system", "content": "步骤 1/2: 获取 OpenSpec ID..."}
                
                spec_id = None
                async for event in self._extract_spec_id_via_list(session, session_id):
                    if event.get("type") == "_spec_id":
                        spec_id = event.get("content")
                    elif event.get("type") != "_collected_output":
                        yield event
                
                if not spec_id:
                    yield {"type": "error", "content": "无法获取 OpenSpec ID，流程终止"}
                    return
                
                # 返回提取的 ID
                yield {"type": "spec_id", "content": spec_id}
                
                # 步骤2: 执行 preview + prompt
                yield {"type": "system", "content": f"步骤 2/2: 执行 preview (ID: {spec_id})..."}
                
                preview_prompt = OpenSpecPromptBuilder.build_preview_prompt(spec_id, user_prompt)
                async for event in self._execute_single_query(session, preview_prompt, session_id):
                    if event.get("type") != "_collected_output":
                        yield event
                
                yield {"type": "system", "content": "=== preview 流程完成 ==="}
                yield {"type": "complete", "content": "preview 流程执行完成", "spec_id": spec_id}
                
            elif task_type == "build":
                # === BUILD 流程 ===
                yield {"type": "system", "content": "=== 开始执行 build 流程 ==="}
                
                # 步骤1: 执行 openspec list 提取 ID
                yield {"type": "system", "content": "步骤 1/3: 获取 OpenSpec ID..."}
                
                spec_id = None
                async for event in self._extract_spec_id_via_list(session, session_id):
                    if event.get("type") == "_spec_id":
                        spec_id = event.get("content")
                    elif event.get("type") != "_collected_output":
                        yield event
                
                if not spec_id:
                    yield {"type": "error", "content": "无法获取 OpenSpec ID，流程终止"}
                    return
                
                # 返回提取的 ID
                yield {"type": "spec_id", "content": spec_id}
                
                # 步骤2: 执行 apply
                yield {"type": "system", "content": f"步骤 2/3: 执行 apply (ID: {spec_id})..."}
                
                apply_prompt = OpenSpecPromptBuilder.build_apply_prompt(spec_id)
                async for event in self._execute_single_query(session, apply_prompt, session_id):
                    if event.get("type") != "_collected_output":
                        yield event
                
                # 步骤3: 执行 archive
                yield {"type": "system", "content": "步骤 3/3: 执行 archive..."}
                
                archive_prompt = OpenSpecPromptBuilder.build_archive_prompt()
                async for event in self._execute_single_query(session, archive_prompt, session_id):
                    if event.get("type") != "_collected_output":
                        yield event
                
                yield {"type": "system", "content": "=== build 流程完成 ==="}
                yield {"type": "complete", "content": "build 流程执行完成", "spec_id": spec_id}
                
            else:
                yield {"type": "error", "content": f"未知的 task_type: {task_type}"}
                
        except asyncio.CancelledError:
            logger.info(f"OpenSpec stream cancelled for session: {session_id}")
            yield {"type": "interrupted", "message": "Stream cancelled"}
            
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
            logger.exception(f"Error in OpenSpec streaming execution for session {session_id}")
            yield {"type": "error", "content": str(e)}
            
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
