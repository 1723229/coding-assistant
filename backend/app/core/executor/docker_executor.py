# -*- coding: utf-8 -*-
"""
Docker executor for sandbox task execution.

This module provides the main executor implementation that:
- Manages container lifecycle
- Executes tasks via container API
- Proxies SSE streams from containers
"""

import os
import subprocess
import threading
import logging
from typing import Dict, Any, Optional, AsyncGenerator

import httpx

from app.core.executor.base import ExecutorBase, ExecutorError, ContainerExecutionError
from app.core.executor.constants import (
    DEFAULT_API_ENDPOINT,
    DEFAULT_CANCEL_ENDPOINT,
    WORKSPACE_MOUNT_PATH,
)
from app.core.executor.container_manager import ContainerManager, get_container_manager
from app.core.executor.stream_proxy import StreamProxy
from app.config.settings import ExecutorConfig

logger = logging.getLogger(__name__)


class SandboxDockerExecutor(ExecutorBase):
    """
    Docker executor for sandbox task execution.
    
    Each session gets its own container. The container runs the executor service
    which handles Claude Code execution in an isolated environment.
    """
    
    def __init__(
        self,
        container_manager: Optional[ContainerManager] = None,
        stream_proxy: Optional[StreamProxy] = None,
    ):
        """
        Initialize sandbox executor.
        
        Args:
            container_manager: Container manager instance
            stream_proxy: Stream proxy instance
        """
        self._container_manager = container_manager or get_container_manager()
        self._stream_proxy = stream_proxy or StreamProxy()
    
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
        try:
            # Get or create container
            container = await self._container_manager.get_or_create_container(
                session_id=session_id,
                workspace_path=workspace_path,
            )
            
            # Build request data
            request_data = {
                "session_id": session_id,
                "workspace_path": WORKSPACE_MOUNT_PATH,
                "prompt": prompt,
                **kwargs,
            }
            
            # Send request to container
            url = f"{container.api_base_url}{DEFAULT_API_ENDPOINT}"
            logger.info(f"Sending task to {url}")
            
            async with httpx.AsyncClient(timeout=ExecutorConfig.REQUEST_TIMEOUT) as client:
                response = await client.post(url, json=request_data)
                response.raise_for_status()
                result = response.json()
            
            logger.info(f"Task completed for session {session_id}")
            return result
            
        except httpx.TimeoutException:
            logger.error(f"Request timeout for session {session_id}")
            return {
                "status": "failed",
                "error_message": "Request timeout",
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for session {session_id}: {e}")
            return {
                "status": "failed",
                "error_message": str(e),
            }
        except Exception as e:
            logger.exception(f"Error executing task for session {session_id}")
            return {
                "status": "failed",
                "error_message": str(e),
            }
    
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
        try:
            # Get or create container
            container = await self._container_manager.get_or_create_container(
                session_id=session_id,
                workspace_path=workspace_path,
            )
            
            # Build request data
            request_data = {
                "session_id": session_id,
                "workspace_path": WORKSPACE_MOUNT_PATH,
                "prompt": prompt,
                **kwargs,
            }
            
            # Proxy stream from container
            async for event in self._stream_proxy.proxy_stream(container, request_data):
                yield event
                
        except Exception as e:
            logger.exception(f"Error in stream execution for session {session_id}")
            yield {
                "type": "error",
                "content": str(e),
            }
    
    async def cancel(self, session_id: str) -> bool:
        """
        Cancel a running task.
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if cancellation was successful
        """
        try:
            container = await self._container_manager.get_container_info(session_id)
            
            if not container:
                logger.warning(f"No container found for session {session_id}")
                return False
            
            # Send cancel request to container
            url = f"{container.api_base_url}{DEFAULT_CANCEL_ENDPOINT}"
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    url,
                    params={"session_id": session_id},
                )
                response.raise_for_status()
                result = response.json()
            
            logger.info(f"Cancel request sent for session {session_id}: {result}")
            return result.get("status") == "success"
            
        except Exception as e:
            logger.exception(f"Error cancelling task for session {session_id}")
            return False
    
    async def cleanup(self, session_id: str) -> bool:
        """
        Cleanup resources for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if cleanup was successful
        """
        return await self._container_manager.remove_container(session_id)
    
    async def health_check(self, session_id: str) -> Dict[str, Any]:
        """
        Perform health check on container.
        
        Args:
            session_id: Session identifier
            
        Returns:
            dict: Health check result
        """
        return await self._container_manager.health_check(session_id)
    
    async def get_container_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get status of a container.
        
        Args:
            session_id: Session identifier
            
        Returns:
            dict: Container status with port information
        """
        container = await self._container_manager.get_container_info(session_id)
        
        if container:
            return {
                "status": "running",
                "container_name": container.name,
                "api_port": container.api_port,
                "code_port": container.code_port,
                "api_url": container.api_base_url,
                "code_url": container.code_base_url,
            }
        else:
            return {
                "status": "not_found",
            }
    
    async def create_workspace(
        self,
        session_id: str,
        workspace_path: str,
    ) -> Dict[str, Any]:
        """
        Create a workspace container for a session.
        
        Args:
            session_id: Session identifier
            workspace_path: Host path to workspace directory
            
        Returns:
            dict: Container information with port mappings
        """
        try:
            container = await self._container_manager.get_or_create_container(
                session_id=session_id,
                workspace_path=workspace_path,
            )

            # 判断根目录是否存在startup.sh脚本，存在则在容器中执行（异步线程，不阻塞）
            self._run_startup_script_async(container.name, workspace_path)

            result = {
                "id": container.name,
                "name": container.name,
                "api_port": container.api_port,
                "code_port": container.code_port,
                "api_url": container.api_base_url,
                "code_url": container.code_base_url,
                "status": container.status,
                "workspace_path": workspace_path,
            }

            logger.info(f"Created workspace container {result}")

            return result
        except Exception as e:
            logger.error(f"Failed to create workspace for session {session_id}: {e}")
            raise ExecutorError(f"Failed to create workspace: {e}")
    
    async def stop_container(self, session_id: str) -> bool:
        """
        Stop a container for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if stopped successfully
        """
        return await self._container_manager.remove_container(session_id)
    
    async def restart_container(self, session_id: str, workspace_path: str = "") -> bool:
        """
        Restart a container for a session.
        
        Args:
            session_id: Session identifier
            workspace_path: Workspace path (required for recreation)
            
        Returns:
            bool: True if restarted successfully
        """
        try:
            # Remove existing container
            await self._container_manager.remove_container(session_id)
            
            # Recreate container if workspace_path provided
            if workspace_path:
                await self._container_manager.get_or_create_container(
                    session_id=session_id,
                    workspace_path=workspace_path,
                )
            
            return True
        except Exception as e:
            logger.error(f"Failed to restart container for session {session_id}: {e}")
            return False
    
    def get_container_manager(self) -> ContainerManager:
        """Get the container manager instance."""
        return self._container_manager
    
    def _run_startup_script_async(
        self,
        container_name: str,
        workspace_path: str,
    ) -> None:
        """
        Check and run startup.sh script in a separate thread (non-blocking).
        
        Args:
            container_name: Name of the container
            workspace_path: Host path to workspace directory
        """
        startup_script = os.path.join(workspace_path, "startup.sh")
        
        # Check if startup.sh exists on host
        if not os.path.exists(startup_script):
            logger.debug(f"No startup.sh found in {workspace_path}")
            return
        
        # Run in separate thread to avoid blocking
        thread = threading.Thread(
            target=self._run_startup_script_sync,
            args=(container_name, workspace_path),
            daemon=True,
        )
        thread.start()
        logger.info(f"Started startup.sh execution thread for container {container_name}")
    
    def _run_startup_script_sync(
        self,
        container_name: str,
        workspace_path: str,
    ) -> bool:
        """
        Synchronously run startup.sh script in container (called from thread).
        
        Args:
            container_name: Name of the container
            workspace_path: Host path to workspace directory
            
        Returns:
            bool: True if script was executed successfully
        """
        try:
            logger.info(f"Found startup.sh in {workspace_path}, executing in container {container_name}")
            
            # Make script executable in container
            chmod_cmd = [
                "docker", "exec", "-u", "root",
                container_name,
                "chmod", "+x", f"{WORKSPACE_MOUNT_PATH}/startup.sh"
            ]
            
            chmod_result = subprocess.run(
                chmod_cmd,
                capture_output=True,
                text=True,
            )
            
            if chmod_result.returncode != 0:
                logger.warning(f"Failed to chmod startup.sh: {chmod_result.stderr}")
                return False
            
            # Execute startup script in background (detached)
            exec_cmd = [
                "docker", "exec", "-d",
                container_name,
                "/bin/bash", "-c",
                f"cd {WORKSPACE_MOUNT_PATH} && ./startup.sh > /tmp/startup.log 2>&1"
            ]
            
            exec_result = subprocess.run(
                exec_cmd,
                capture_output=True,
                text=True,
            )
            
            if exec_result.returncode != 0:
                logger.warning(f"Failed to execute startup.sh: {exec_result.stderr}")
                return False
            
            logger.info(f"Successfully started startup.sh in container {container_name}")
            return True
            
        except Exception as e:
            logger.exception(f"Error running startup.sh in container {container_name}: {e}")
            return False


# Global executor instance
_sandbox_executor: Optional[SandboxDockerExecutor] = None


def get_sandbox_executor() -> SandboxDockerExecutor:
    """Get global sandbox executor instance."""
    global _sandbox_executor
    if _sandbox_executor is None:
        _sandbox_executor = SandboxDockerExecutor()
    return _sandbox_executor

