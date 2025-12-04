# -*- coding: utf-8 -*-
"""
Base Agent class that all specific agents should inherit from.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task execution status."""
    INITIALIZED = "initialized"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Agent:
    """
    Base Agent class that all specific agents should inherit from.
    """

    def get_name(self) -> str:
        """
        Get the name of the agent.
        
        Returns:
            str: The name of the agent
        """
        return self.__class__.__name__

    def __init__(self, task_data: Dict[str, Any]):
        """
        Initialize the base agent.

        Args:
            task_data: The task data dictionary
        """
        self.task_data = task_data
        self.session_id = task_data.get("session_id", "")
        self.workspace_path = task_data.get("workspace_path", "/workspace")
        self.prompt = task_data.get("prompt", "")
        self.execution_status = TaskStatus.INITIALIZED

    def handle(self) -> Tuple[TaskStatus, Optional[str], Optional[Dict[str, Any]]]:
        """
        Unified entry point for agent execution.
        
        Returns:
            tuple: (status: TaskStatus, error_message: str or None, result: dict or None)
        """
        try:
            self.execution_status = TaskStatus.RUNNING
            logger.info(f"Agent[{self.get_name()}][{self.session_id}] Starting execution")
            
            result = self.execute()
            
            logger.info(f"Agent[{self.get_name()}][{self.session_id}] Execution completed")
            return TaskStatus.COMPLETED, None, result
            
        except Exception as e:
            error_msg = f"Agent[{self.get_name()}][{self.session_id}] Exception during execute: {str(e)}"
            logger.exception(error_msg)
            return TaskStatus.FAILED, str(e), None

    def execute(self) -> Optional[Dict[str, Any]]:
        """
        Execute the agent's task.

        Returns:
            Optional[Dict[str, Any]]: Execution result data
        """
        raise NotImplementedError("Subclasses must implement execute()")

    def cancel(self) -> bool:
        """
        Cancel the current execution.
        
        Returns:
            bool: True if cancellation was successful
        """
        return False

    def initialize(self) -> TaskStatus:
        """
        Initialize the agent with configuration from task_data.
        
        Returns:
            TaskStatus: Initialization status
        """
        logger.info(f"Agent[{self.get_name()}][{self.session_id}] Initialized")
        return TaskStatus.SUCCESS

