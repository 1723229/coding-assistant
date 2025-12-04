# -*- coding: utf-8 -*-
"""
Agent service for managing agent sessions and execution.
"""

import logging
import threading
import time
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass

from executor.agents.base import Agent, TaskStatus
from executor.agents.claude_code import ClaudeCodeAgent

logger = logging.getLogger(__name__)


@dataclass
class AgentSession:
    """Agent session data."""
    agent: Agent
    created_at: float


class AgentService:
    """
    Service for managing agent sessions and execution.
    Singleton pattern to ensure single instance across the application.
    """
    
    _instance: Optional['AgentService'] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._agent_sessions: Dict[str, AgentSession] = {}
        return cls._instance

    def get_agent(self, session_id: str) -> Optional[Agent]:
        """Get existing agent for session."""
        session = self._agent_sessions.get(session_id)
        return session.agent if session else None

    def create_agent(self, task_data: Dict[str, Any]) -> Optional[Agent]:
        """
        Create a new agent for the task.
        
        Args:
            task_data: Task data containing session_id, workspace_path, prompt, etc.
            
        Returns:
            Created agent instance or None if creation failed
        """
        session_id = task_data.get("session_id", "")
        
        # Check if agent already exists
        if existing_agent := self.get_agent(session_id):
            logger.info(f"[{session_id}] Reusing existing agent")
            # Update prompt if provided
            if "prompt" in task_data:
                existing_agent.prompt = task_data["prompt"]
            return existing_agent

        try:
            agent_type = task_data.get("agent_type", "claude_code").lower()
            
            if agent_type == "claude_code":
                agent = ClaudeCodeAgent(task_data)
            else:
                logger.error(f"[{session_id}] Unsupported agent type: {agent_type}")
                return None

            # Initialize agent
            init_status = agent.initialize()
            if init_status != TaskStatus.SUCCESS:
                logger.error(f"[{session_id}] Failed to initialize agent: {init_status}")
                return None

            # Store session
            self._agent_sessions[session_id] = AgentSession(
                agent=agent,
                created_at=time.time()
            )
            logger.info(f"[{session_id}] Agent created successfully")
            return agent

        except Exception as e:
            logger.exception(f"[{session_id}] Exception during agent creation: {e}")
            return None

    def execute_task(self, task_data: Dict[str, Any]) -> Tuple[TaskStatus, Optional[str], Optional[Dict[str, Any]]]:
        """
        Execute a task with the appropriate agent.
        
        Args:
            task_data: Task data containing session_id, workspace_path, prompt, etc.
            
        Returns:
            Tuple of (status, error_message, result_data)
        """
        session_id = task_data.get("session_id", "")
        
        try:
            # Get or create agent
            agent = self.get_agent(session_id)
            
            if agent:
                # Update prompt for existing agent
                if "prompt" in task_data:
                    agent.prompt = task_data["prompt"]
            else:
                agent = self.create_agent(task_data)
                
            if not agent:
                return TaskStatus.FAILED, "Failed to create agent", None
            
            # Execute task
            return agent.handle()
            
        except Exception as e:
            logger.exception(f"[{session_id}] Task execution error: {e}")
            return TaskStatus.FAILED, str(e), None

    def cancel_task(self, session_id: str) -> Tuple[TaskStatus, Optional[str]]:
        """
        Cancel a running task.
        
        Args:
            session_id: Session ID to cancel
            
        Returns:
            Tuple of (status, message)
        """
        session = self._agent_sessions.get(session_id)
        if not session:
            return TaskStatus.FAILED, f"No session found for {session_id}"

        try:
            if hasattr(session.agent, 'cancel'):
                success = session.agent.cancel()
                if success:
                    return TaskStatus.SUCCESS, "Task cancelled"
                else:
                    return TaskStatus.FAILED, "Cancel failed"
            else:
                return TaskStatus.FAILED, "Agent does not support cancellation"
        except Exception as e:
            logger.exception(f"[{session_id}] Error cancelling task: {e}")
            return TaskStatus.FAILED, str(e)

    def delete_session(self, session_id: str) -> Tuple[TaskStatus, Optional[str]]:
        """
        Delete an agent session.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            Tuple of (status, message)
        """
        if session_id not in self._agent_sessions:
            return TaskStatus.FAILED, f"No session found for {session_id}"

        try:
            session = self._agent_sessions.pop(session_id)
            
            # Close client if it's a Claude Code agent
            if isinstance(session.agent, ClaudeCodeAgent):
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                loop.run_until_complete(ClaudeCodeAgent.close_client(session_id))
            
            logger.info(f"[{session_id}] Session deleted")
            return TaskStatus.SUCCESS, "Session deleted"
            
        except Exception as e:
            logger.exception(f"[{session_id}] Error deleting session: {e}")
            return TaskStatus.FAILED, str(e)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions."""
        return [
            {
                "session_id": session_id,
                "agent_type": session.agent.get_name(),
                "created_at": session.created_at
            }
            for session_id, session in self._agent_sessions.items()
        ]

    async def close_all_sessions(self) -> Tuple[TaskStatus, str]:
        """Close all agent sessions."""
        try:
            await ClaudeCodeAgent.close_all_clients()
            self._agent_sessions.clear()
            return TaskStatus.SUCCESS, "All sessions closed"
        except Exception as e:
            logger.exception("Error closing all sessions")
            return TaskStatus.FAILED, str(e)

