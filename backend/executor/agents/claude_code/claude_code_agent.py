# -*- coding: utf-8 -*-
"""
Claude Code Agent implementation using Claude Agent SDK.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional, List, ClassVar

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

from executor.agents.base import Agent, TaskStatus
from executor.config import config

logger = logging.getLogger(__name__)


class ClaudeCodeAgent(Agent):
    """
    Claude Code Agent that uses Claude Agent SDK for code assistance.
    """
    
    # Class-level client cache for session reuse
    _clients: ClassVar[Dict[str, ClaudeSDKClient]] = {}

    def __init__(self, task_data: Dict[str, Any]):
        """
        Initialize Claude Code Agent.
        
        Args:
            task_data: Task data containing session_id, workspace_path, prompt, etc.
        """
        super().__init__(task_data)
        self._client: Optional[ClaudeSDKClient] = None
        self._is_connected = False
        self._cancelled = False
        
        # Extract configuration
        self.allowed_tools = task_data.get("allowed_tools", config.DEFAULT_TOOLS.copy())
        self.permission_mode = task_data.get("permission_mode", config.PERMISSION_MODE)
        self.system_prompt = task_data.get("system_prompt")
        self.model = task_data.get("model", config.ANTHROPIC_MODEL)

    def get_name(self) -> str:
        return "ClaudeCodeAgent"

    def _create_options(self) -> ClaudeAgentOptions:
        """Create Claude agent options with proper configuration."""
        if self.system_prompt:
            prompt_config = self.system_prompt
        else:
            prompt_config = {
                "type": "preset",
                "preset": "claude_code",
                "append": "You are helping the user with their coding tasks in a sandbox environment.",
            }
        
        options = ClaudeAgentOptions(
            allowed_tools=self.allowed_tools,
            system_prompt=prompt_config,
            permission_mode=self.permission_mode,
            cwd=self.workspace_path,
            include_partial_messages=True,
            model=self.model,
        )
        return options

    async def _connect(self) -> ClaudeSDKClient:
        """Connect to Claude SDK client."""
        # Check if we have a cached client for this session
        if self.session_id in self._clients:
            self._client = self._clients[self.session_id]
            self._is_connected = True
            logger.info(f"Reusing existing client for session: {self.session_id}")
            return self._client
            
        options = self._create_options()
        self._client = ClaudeSDKClient(options=options)
        await self._client.connect()
        self._is_connected = True
        
        # Cache the client
        self._clients[self.session_id] = self._client
        logger.info(f"Connected to Claude SDK for session: {self.session_id}")
        return self._client

    async def _disconnect(self):
        """Disconnect from Claude SDK client."""
        if self._client is not None and self._is_connected:
            try:
                await self._client.disconnect()
                logger.info(f"Disconnected from Claude SDK for session: {self.session_id}")
            except RuntimeError as e:
                if "cancel scope" not in str(e).lower():
                    logger.warning(f"Error during disconnect: {e}")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self._is_connected = False
                # Remove from cache
                if self.session_id in self._clients:
                    del self._clients[self.session_id]

    async def _execute_async(self) -> Dict[str, Any]:
        """
        Execute the Claude Code task asynchronously.
        
        Returns:
            Dict containing execution results
        """
        client = await self._connect()
        
        messages = []
        result_data = {
            "text_content": "",
            "tool_uses": [],
            "thinking": [],
            "metadata": {},
        }
        
        try:
            # Send query with session_id for multi-turn conversation support
            await client.query(self.prompt, session_id=self.session_id)
            logger.debug(f"Sent query with session_id: {self.session_id}")
            
            # Process responses
            async for msg in client.receive_response():
                if self._cancelled:
                    logger.info(f"Execution cancelled for session: {self.session_id}")
                    break
                    
                parsed = self._parse_message(msg)
                messages.extend(parsed)
                
                # Aggregate results
                for m in parsed:
                    if m["type"] == "text":
                        result_data["text_content"] += m["content"]
                    elif m["type"] == "tool_use":
                        result_data["tool_uses"].append({
                            "tool_name": m.get("tool_name"),
                            "tool_input": m.get("tool_input"),
                        })
                    elif m["type"] == "thinking":
                        result_data["thinking"].append(m["content"])
                    elif m["type"] == "result":
                        result_data["metadata"] = m.get("metadata", {})
            
            result_data["messages"] = messages
            return result_data
            
        except Exception as e:
            logger.error(f"Error during execution: {e}", exc_info=True)
            raise

    def _parse_message(self, msg: Any) -> List[Dict[str, Any]]:
        """Parse SDK message into dictionary format."""
        messages = []
        
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    messages.append({
                        "type": "text",
                        "content": block.text,
                    })
                elif isinstance(block, ThinkingBlock):
                    messages.append({
                        "type": "thinking",
                        "content": block.thinking,
                    })
                elif isinstance(block, ToolUseBlock):
                    messages.append({
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
                    messages.append({
                        "type": "tool_result",
                        "content": content[:500] + "..." if len(content) > 500 else content,
                        "metadata": {
                            "tool_use_id": block.tool_use_id,
                            "is_error": block.is_error,
                        },
                    })
                    
        elif isinstance(msg, SystemMessage):
            messages.append({
                "type": "system",
                "content": json.dumps(msg.data) if msg.data else msg.subtype,
                "metadata": {"subtype": msg.subtype},
            })
            
        elif isinstance(msg, ResultMessage):
            messages.append({
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
        
        return messages

    def execute(self) -> Optional[Dict[str, Any]]:
        """
        Execute the Claude Code task synchronously.
        
        Returns:
            Dict containing execution results
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._execute_async())

    def cancel(self) -> bool:
        """Cancel the current execution."""
        self._cancelled = True
        if self._client is not None and self._is_connected:
            try:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self._client.interrupt())
                logger.info(f"Sent interrupt for session: {self.session_id}")
                return True
            except Exception as e:
                logger.warning(f"Error during interrupt: {e}")
        return False

    @classmethod
    async def close_client(cls, session_id: str):
        """Close client for a specific session."""
        if session_id in cls._clients:
            client = cls._clients.pop(session_id)
            try:
                await client.disconnect()
                logger.info(f"Closed client for session: {session_id}")
            except Exception as e:
                logger.warning(f"Error closing client for session {session_id}: {e}")

    @classmethod
    async def close_all_clients(cls):
        """Close all cached clients."""
        session_ids = list(cls._clients.keys())
        for session_id in session_ids:
            await cls.close_client(session_id)
        logger.info(f"Closed all {len(session_ids)} clients")

