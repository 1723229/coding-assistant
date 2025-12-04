# -*- coding: utf-8 -*-
"""
Container lifecycle manager for sandbox execution.

This module handles:
- Container creation with proper configuration
- Container health checking
- Container cleanup and removal
"""

import os
import asyncio
import subprocess
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import httpx

from app.core.executor.constants import (
    CONTAINER_OWNER,
    DEFAULT_DOCKER_HOST,
    DEFAULT_TIMEZONE,
    DEFAULT_LOCALE,
    WORKSPACE_MOUNT_PATH,
    DEFAULT_EXECUTOR_IMAGE,
    DEFAULT_MEMORY_LIMIT,
    DEFAULT_CPU_COUNT,
    DEFAULT_HEALTH_ENDPOINT,
    HEALTH_CHECK_TIMEOUT,
    INTERNAL_API_PORT,
    INTERNAL_CODE_PORT,
)
from app.core.executor.utils import (
    find_available_ports,
    check_container_exists,
    check_container_running,
    get_container_ports,
    delete_container,
    generate_container_name,
)
from app.config.settings import ExecutorConfig

logger = logging.getLogger(__name__)


@dataclass
class ContainerInfo:
    """Container information with dual port mapping."""
    name: str
    session_id: str
    api_port: int              # External port for FastAPI executor service
    code_port: int             # External port for static file server
    workspace_path: str
    status: str = "created"
    created_at: datetime = field(default_factory=datetime.now)
    
    # Backward compatibility
    @property
    def port(self) -> int:
        """Get API port (backward compatibility)."""
        return self.api_port
    
    @property
    def api_base_url(self) -> str:
        """Get the base URL for container API.
        
        Uses 127.0.0.1 (localhost) for host-to-container communication.
        The api_port is mapped from host to container's internal 8080 port.
        """
        return f"http://127.0.0.1:{self.api_port}"
    
    @property
    def code_base_url(self) -> str:
        """Get the base URL for code static file server.
        
        Uses 127.0.0.1 (localhost) for host-to-container communication.
        The code_port is mapped from host to container's internal 80 port.
        """
        return f"http://127.0.0.1:{self.code_port}"


class ContainerManager:
    """
    Manager for sandbox container lifecycle.
    
    Handles container creation, health checking, and cleanup.
    """
    
    _instance: Optional['ContainerManager'] = None
    
    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._containers: Dict[str, ContainerInfo] = {}
            cls._instance._executor_image = DEFAULT_EXECUTOR_IMAGE
        return cls._instance
    
    def __init__(self, executor_image: Optional[str] = None):
        """
        Initialize container manager.
        
        Args:
            executor_image: Docker image to use for executor containers
        """
        if executor_image:
            self._executor_image = executor_image
    
    def _build_docker_command(
        self,
        container_name: str,
        session_id: str,
        workspace_path: str,
        api_port: int,
        code_port: int,
    ) -> List[str]:
        """Build docker run command with dual port mapping.
        
        Args:
            container_name: Name for the container
            session_id: Session identifier
            workspace_path: Host path to workspace directory
            api_port: External port for FastAPI service (maps to internal 8080)
            code_port: External port for code service (maps to internal 80)
        """
        cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            # Labels for container management
            "--label", f"owner={CONTAINER_OWNER}",
            "--label", f"session_id={session_id}",
            # Environment variables
            "-e", f"PORT={INTERNAL_API_PORT}",  # Internal API port is always 8080
            "-e", f"TZ={DEFAULT_TIMEZONE}",
            "-e", f"LANG={DEFAULT_LOCALE}",
            "-e", f"SESSION_ID={session_id}",
            "-e", f"WORKSPACE_PATH={WORKSPACE_MOUNT_PATH}",
            # Resource limits
            "-m", DEFAULT_MEMORY_LIMIT,
            "--cpus", str(DEFAULT_CPU_COUNT),
        ]
        
        # Pass Claude API configuration from config.yaml
        if ExecutorConfig.ANTHROPIC_API_KEY:
            cmd.extend(["-e", f"ANTHROPIC_API_KEY={ExecutorConfig.ANTHROPIC_API_KEY}"])
        
        if ExecutorConfig.ANTHROPIC_BASE_URL:
            cmd.extend(["-e", f"ANTHROPIC_BASE_URL={ExecutorConfig.ANTHROPIC_BASE_URL}"])
        
        if ExecutorConfig.ANTHROPIC_MODEL:
            cmd.extend(["-e", f"ANTHROPIC_MODEL={ExecutorConfig.ANTHROPIC_MODEL}"])
        
        # Mount workspace (create if not exists)
        if workspace_path:
            abs_workspace = os.path.abspath(workspace_path)
            # Ensure workspace directory exists
            os.makedirs(abs_workspace, exist_ok=True)
            logger.info(f"Mounting workspace: {abs_workspace} -> {WORKSPACE_MOUNT_PATH}")
            cmd.extend(["-v", f"{abs_workspace}:{WORKSPACE_MOUNT_PATH}"])
        
        # Port mapping: external_port -> internal_port
        # API service: api_port -> 8080
        cmd.extend(["-p", f"{api_port}:{INTERNAL_API_PORT}"])
        # Code service: code_port -> 80
        cmd.extend(["-p", f"{code_port}:{INTERNAL_CODE_PORT}"])
        
        # Network configuration
        network = os.getenv("DOCKER_NETWORK")
        if network:
            cmd.extend(["--network", network])
        
        # Image
        cmd.append(self._executor_image)
        
        return cmd
    
    async def _wait_for_container_ready(
        self,
        api_port: int,
        timeout: int = HEALTH_CHECK_TIMEOUT,
    ) -> bool:
        """
        Wait for container to be ready by polling health endpoint.
        
        Args:
            api_port: External API port (mapped to internal 8080)
            timeout: Maximum wait time in seconds
            
        Returns:
            bool: True if container is ready
        """
        # Use localhost for host-to-container communication
        url = f"http://127.0.0.1:{api_port}{DEFAULT_HEALTH_ENDPOINT}"
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                async with httpx.AsyncClient(timeout=2) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        logger.info(f"Container ready on API port {api_port}")
                        return True
            except Exception:
                pass
            await asyncio.sleep(0.5)
        
        logger.warning(f"Container on API port {api_port} not ready after {timeout}s")
        return False
    
    async def get_or_create_container(
        self,
        session_id: str,
        workspace_path: str,
    ) -> ContainerInfo:
        """
        Get existing container or create a new one for the session.
        
        Args:
            session_id: Session identifier
            workspace_path: Host path to workspace directory
            
        Returns:
            ContainerInfo: Container information with api_port and code_port
            
        Raises:
            RuntimeError: If container creation fails
        """
        container_name = generate_container_name(session_id)
        
        # Check if we have a cached container info
        if session_id in self._containers:
            info = self._containers[session_id]
            if check_container_running(container_name):
                logger.info(f"Reusing existing container: {container_name}")
                return info
        
        # Check if container already exists and is running
        if check_container_running(container_name):
            ports = get_container_ports(container_name)
            if ports and "api_port" in ports:
                logger.info(f"Found running container: {container_name} on ports {ports}")
                info = ContainerInfo(
                    name=container_name,
                    session_id=session_id,
                    api_port=ports["api_port"],
                    code_port=ports.get("code_port", 0),
                    workspace_path=workspace_path,
                    status="running",
                )
                self._containers[session_id] = info
                return info
        
        # If container exists but not running, remove it first
        if check_container_exists(container_name):
            logger.info(f"Removing stopped container: {container_name}")
            delete_container(container_name)
        
        # Create new container
        try:
            api_port, code_port = find_available_ports()
            cmd = self._build_docker_command(
                container_name=container_name,
                session_id=session_id,
                workspace_path=workspace_path,
                api_port=api_port,
                code_port=code_port,
            )
            
            logger.info(f"Starting container {container_name} with API port {api_port}, code port {code_port}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            container_id = result.stdout.strip()
            
            logger.info(f"Started container {container_name} with ID {container_id}")
            
            # Wait for container to be ready (check API port)
            ready = await self._wait_for_container_ready(api_port)
            
            info = ContainerInfo(
                name=container_name,
                session_id=session_id,
                api_port=api_port,
                code_port=code_port,
                workspace_path=workspace_path,
                status="running" if ready else "starting",
            )
            self._containers[session_id] = info
            
            if not ready:
                logger.warning(f"Container {container_name} may not be fully ready")
            
            return info
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Docker run error: {e.stderr}")
            raise RuntimeError(f"Failed to create container: {e.stderr}")
        except Exception as e:
            logger.error(f"Error creating container: {e}")
            raise RuntimeError(f"Failed to create container: {e}")
    
    async def remove_container(self, session_id: str) -> bool:
        """
        Remove a container for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if container was removed
        """
        container_name = generate_container_name(session_id)
        result = delete_container(container_name)
        
        if session_id in self._containers:
            del self._containers[session_id]
        
        return result.get("status") == "success"
    
    async def get_container_info(self, session_id: str) -> Optional[ContainerInfo]:
        """
        Get container info for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            ContainerInfo or None if not found
        """
        if session_id in self._containers:
            info = self._containers[session_id]
            if check_container_running(info.name):
                return info
        
        container_name = generate_container_name(session_id)
        if check_container_running(container_name):
            ports = get_container_ports(container_name)
            if ports and "api_port" in ports:
                info = ContainerInfo(
                    name=container_name,
                    session_id=session_id,
                    api_port=ports["api_port"],
                    code_port=ports.get("code_port", 0),
                    workspace_path="",
                    status="running",
                )
                self._containers[session_id] = info
                return info
        
        return None
    
    async def health_check(self, session_id: str) -> Dict[str, Any]:
        """
        Perform health check on container.
        
        Args:
            session_id: Session identifier
            
        Returns:
            dict: Health check result with port information
        """
        info = await self.get_container_info(session_id)
        
        if not info:
            return {
                "healthy": False,
                "status": "not_found",
                "message": "Container does not exist",
            }
        
        try:
            url = f"{info.api_base_url}{DEFAULT_HEALTH_ENDPOINT}"
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return {
                        "healthy": True,
                        "status": "running",
                        "message": "Container is healthy",
                        "container": info.name,
                        "api_port": info.api_port,
                        "code_port": info.code_port,
                        "api_url": info.api_base_url,
                        "code_url": info.code_base_url,
                    }
                else:
                    return {
                        "healthy": False,
                        "status": "unhealthy",
                        "message": f"Health check returned {response.status_code}",
                    }
        except Exception as e:
            return {
                "healthy": False,
                "status": "error",
                "message": str(e),
            }
    
    async def cleanup_all(self) -> int:
        """
        Remove all managed containers.
        
        Returns:
            int: Number of containers removed
        """
        session_ids = list(self._containers.keys())
        removed = 0
        
        for session_id in session_ids:
            if await self.remove_container(session_id):
                removed += 1
        
        logger.info(f"Cleaned up {removed} containers")
        return removed


# Global container manager instance
_container_manager: Optional[ContainerManager] = None


def get_container_manager() -> ContainerManager:
    """Get global container manager instance."""
    global _container_manager
    if _container_manager is None:
        _container_manager = ContainerManager()
    return _container_manager

