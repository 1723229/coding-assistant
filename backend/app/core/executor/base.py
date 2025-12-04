# -*- coding: utf-8 -*-
"""
Base executor interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncGenerator


class ExecutorError(Exception):
    """Base exception for executor operations."""
    
    def __init__(self, message: str, operation: str, details: Optional[dict] = None):
        super().__init__(message)
        self.operation = operation
        self.details = details or {}


class ContainerNotFoundError(ExecutorError):
    """Exception when container is not found."""
    pass


class ContainerExecutionError(ExecutorError):
    """Exception when task execution fails."""
    pass


class ExecutorBase(ABC):
    """
    Abstract base class for executors.
    
    Executors are responsible for:
    - Managing execution environments (containers, VMs, etc.)
    - Executing tasks in isolated environments
    - Streaming task results back to the caller
    """
    
    @abstractmethod
    async def execute(
        self,
        session_id: str,
        workspace_path: str,
        prompt: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute a task synchronously.
        
        Args:
            session_id: Session identifier
            workspace_path: Host path to workspace directory
            prompt: Task prompt
            **kwargs: Additional task parameters
            
        Returns:
            dict: Execution result
        """
        pass
    
    @abstractmethod
    async def execute_stream(
        self,
        session_id: str,
        workspace_path: str,
        prompt: str,
        **kwargs,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute a task with streaming response.
        
        Args:
            session_id: Session identifier
            workspace_path: Host path to workspace directory
            prompt: Task prompt
            **kwargs: Additional task parameters
            
        Yields:
            dict: Event dictionaries for SSE streaming
        """
        pass
    
    @abstractmethod
    async def cancel(self, session_id: str) -> bool:
        """
        Cancel a running task.
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if cancellation was successful
        """
        pass
    
    @abstractmethod
    async def cleanup(self, session_id: str) -> bool:
        """
        Cleanup resources for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if cleanup was successful
        """
        pass

