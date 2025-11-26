"""Docker container management service for workspace isolation."""

import os
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps

import docker
from docker.models.containers import Container
from docker.errors import NotFound, APIError, ImageNotFound

from ..config import get_settings

settings = get_settings()


class ContainerStatus(str, Enum):
    """Container status enum."""
    RUNNING = "running"
    STOPPED = "stopped"
    CREATED = "created"
    EXITED = "exited"
    PAUSED = "paused"
    DEAD = "dead"
    UNKNOWN = "unknown"


class DockerError(Exception):
    """Base exception for Docker operations."""
    
    def __init__(self, message: str, operation: str, details: Optional[dict] = None):
        super().__init__(message)
        self.operation = operation
        self.details = details or {}


class ContainerNotFoundError(DockerError):
    """Exception when container is not found."""
    pass


class ContainerExecutionError(DockerError):
    """Exception when command execution fails."""
    pass


@dataclass
class ContainerInfo:
    """Container information."""
    id: str
    name: str
    status: ContainerStatus
    workspace_path: str
    created_at: Optional[datetime] = None
    health_status: Optional[str] = None
    
    @classmethod
    def from_container(cls, container: Container, workspace_path: str = "") -> "ContainerInfo":
        """Create ContainerInfo from Docker container."""
        # Parse status
        try:
            status = ContainerStatus(container.status)
        except ValueError:
            status = ContainerStatus.UNKNOWN
            
        # Get creation time
        created_at = None
        if hasattr(container, 'attrs') and container.attrs.get('Created'):
            try:
                created_str = container.attrs['Created'][:26]  # Trim to microseconds
                created_at = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
            except:
                pass
        
        # Get workspace from mounts if not provided
        if not workspace_path and hasattr(container, 'attrs'):
            for mount in container.attrs.get("Mounts", []):
                if mount.get("Destination") == "/workspace":
                    workspace_path = mount.get("Source", "")
                    break
        
        return cls(
            id=container.id,
            name=container.name,
            status=status,
            workspace_path=workspace_path,
            created_at=created_at,
        )


@dataclass
class ExecutionResult:
    """Result of command execution."""
    exit_code: int
    stdout: str
    stderr: str
    
    @property
    def output(self) -> str:
        """Combined output."""
        return self.stdout + self.stderr
    
    @property
    def success(self) -> bool:
        """Whether execution was successful."""
        return self.exit_code == 0


@dataclass
class ContainerConfig:
    """Configuration for container creation."""
    image: str = field(default_factory=lambda: settings.docker_image)
    memory_limit: str = "2g"
    cpu_quota: int = 100000  # 1 CPU
    cpu_period: int = 100000
    network_mode: Optional[str] = field(default_factory=lambda: settings.docker_network if settings.docker_network else None)
    environment: Dict[str, str] = field(default_factory=dict)
    auto_remove: bool = False
    

def docker_operation(operation_name: str):
    """Decorator for Docker operations with error handling."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except NotFound as e:
                raise ContainerNotFoundError(
                    message=str(e),
                    operation=operation_name,
                )
            except APIError as e:
                raise DockerError(
                    message=str(e),
                    operation=operation_name,
                    details={"status_code": e.status_code if hasattr(e, 'status_code') else None}
                )
            except Exception as e:
                if isinstance(e, DockerError):
                    raise
                raise DockerError(
                    message=str(e),
                    operation=operation_name,
                )
        return wrapper
    return decorator


class DockerService:
    """Service for managing Docker workspace containers."""
    
    CONTAINER_PREFIX = "claude-workspace-"
    
    def __init__(self, config: Optional[ContainerConfig] = None):
        """Initialize Docker client.
        
        Args:
            config: Container configuration (uses defaults if not provided)
        """
        self._client: Optional[docker.DockerClient] = None
        self._config = config or ContainerConfig()
        
    @property
    def client(self) -> docker.DockerClient:
        """Get Docker client, creating if needed."""
        if self._client is None:
            self._client = docker.from_env()
        return self._client
    
    def _get_container_name(self, session_id: str) -> str:
        """Get container name for session."""
        return f"{self.CONTAINER_PREFIX}{session_id[:8]}"
    
    @docker_operation("check_docker")
    async def check_docker_available(self) -> bool:
        """Check if Docker is available and running.
        
        Returns:
            True if Docker is available
        """
        try:
            await asyncio.to_thread(self.client.ping)
            return True
        except Exception:
            return False
    
    @docker_operation("create_workspace")
    async def create_workspace(
        self,
        session_id: str,
        workspace_path: str,
        config: Optional[ContainerConfig] = None,
    ) -> ContainerInfo:
        """Create a workspace container for a session.
        
        Args:
            session_id: Session identifier
            workspace_path: Host path to mount as workspace
            config: Optional container config override
            
        Returns:
            ContainerInfo with container details
        """
        container_name = self._get_container_name(session_id)
        cfg = config or self._config
        
        # Ensure workspace directory exists
        Path(workspace_path).mkdir(parents=True, exist_ok=True)
        
        # Check if container already exists
        try:
            existing = self.client.containers.get(container_name)
            if existing.status != "running":
                existing.start()
            return ContainerInfo.from_container(existing, workspace_path)
        except NotFound:
            pass
        
        # Create new container
        container = await asyncio.to_thread(
            self._create_container,
            container_name,
            workspace_path,
            cfg,
        )
        
        return ContainerInfo.from_container(container, workspace_path)
    
    def _create_container(
        self,
        container_name: str,
        workspace_path: str,
        config: ContainerConfig,
    ) -> Container:
        """Create Docker container (sync helper)."""
        abs_workspace = str(Path(workspace_path).resolve())
        
        # Merge default environment with custom
        environment = {
            "WORKSPACE_PATH": "/workspace",
            **config.environment,
        }
        
        container = self.client.containers.run(
            image=config.image,
            name=container_name,
            detach=True,
            tty=True,
            stdin_open=True,
            working_dir="/workspace",
            volumes={
                abs_workspace: {
                    "bind": "/workspace",
                    "mode": "rw",
                }
            },
            environment=environment,
            mem_limit=config.memory_limit,
            cpu_period=config.cpu_period,
            cpu_quota=config.cpu_quota,
            network_mode=config.network_mode,
            auto_remove=config.auto_remove,
        )
        
        return container
    
    @docker_operation("execute_command")
    async def execute_command(
        self,
        session_id: str,
        command: str,
        workdir: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """Execute command in workspace container.
        
        Args:
            session_id: Session identifier
            command: Command to execute
            workdir: Working directory inside container
            timeout: Execution timeout in seconds
            
        Returns:
            ExecutionResult with exit code and output
        """
        container_name = self._get_container_name(session_id)
        
        try:
            container = self.client.containers.get(container_name)
        except NotFound:
            raise ContainerNotFoundError(
                message=f"Container not found: {container_name}",
                operation="execute_command",
            )
        
        if container.status != "running":
            container.start()
        
        # Execute command
        result = await asyncio.to_thread(
            container.exec_run,
            command,
            workdir=workdir or "/workspace",
            demux=True,
        )
        
        stdout = result.output[0].decode() if result.output[0] else ""
        stderr = result.output[1].decode() if result.output[1] else ""
        
        return ExecutionResult(
            exit_code=result.exit_code,
            stdout=stdout,
            stderr=stderr,
        )
    
    @docker_operation("get_container_status")
    async def get_container_status(self, session_id: str) -> Optional[ContainerInfo]:
        """Get container status for session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            ContainerInfo or None if not found
        """
        container_name = self._get_container_name(session_id)
        
        try:
            container = self.client.containers.get(container_name)
            return ContainerInfo.from_container(container)
        except NotFound:
            return None
    
    @docker_operation("health_check")
    async def health_check(self, session_id: str) -> Dict[str, Any]:
        """Perform health check on container.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict with health check results
        """
        container_info = await self.get_container_status(session_id)
        
        if container_info is None:
            return {
                "healthy": False,
                "status": "not_found",
                "message": "Container does not exist",
            }
        
        if container_info.status != ContainerStatus.RUNNING:
            return {
                "healthy": False,
                "status": str(container_info.status.value),
                "message": f"Container is {container_info.status.value}",
            }
        
        # Try to execute a simple command to verify container is responsive
        try:
            result = await self.execute_command(session_id, "echo 'health check'")
            if result.success:
                return {
                    "healthy": True,
                    "status": "running",
                    "message": "Container is healthy",
                }
            else:
                return {
                    "healthy": False,
                    "status": "unresponsive",
                    "message": f"Health check failed: {result.stderr}",
                }
        except Exception as e:
            return {
                "healthy": False,
                "status": "error",
                "message": str(e),
            }
    
    @docker_operation("stop_container")
    async def stop_container(self, session_id: str, timeout: int = 10) -> bool:
        """Stop workspace container.
        
        Args:
            session_id: Session identifier
            timeout: Stop timeout in seconds
            
        Returns:
            True if stopped, False if not found
        """
        container_name = self._get_container_name(session_id)
        
        try:
            container = self.client.containers.get(container_name)
            await asyncio.to_thread(container.stop, timeout=timeout)
            return True
        except NotFound:
            return False
    
    @docker_operation("remove_container")
    async def remove_container(
        self, 
        session_id: str, 
        force: bool = False,
        remove_volumes: bool = False,
    ) -> bool:
        """Remove workspace container.
        
        Args:
            session_id: Session identifier
            force: Force removal even if running
            remove_volumes: Remove associated volumes
            
        Returns:
            True if removed, False if not found
        """
        container_name = self._get_container_name(session_id)
        
        try:
            container = self.client.containers.get(container_name)
            await asyncio.to_thread(
                container.remove,
                force=force,
                v=remove_volumes,
            )
            return True
        except NotFound:
            return False
    
    @docker_operation("restart_container")
    async def restart_container(self, session_id: str, timeout: int = 10) -> bool:
        """Restart workspace container.
        
        Args:
            session_id: Session identifier
            timeout: Stop timeout before restart
            
        Returns:
            True if restarted
        """
        container_name = self._get_container_name(session_id)
        
        try:
            container = self.client.containers.get(container_name)
            await asyncio.to_thread(container.restart, timeout=timeout)
            return True
        except NotFound:
            return False
    
    @docker_operation("list_containers")
    async def list_containers(self, include_stopped: bool = True) -> list[ContainerInfo]:
        """List all workspace containers.
        
        Args:
            include_stopped: Whether to include stopped containers
            
        Returns:
            List of ContainerInfo
        """
        containers = await asyncio.to_thread(
            self.client.containers.list,
            all=include_stopped,
            filters={"name": self.CONTAINER_PREFIX},
        )
        
        return [ContainerInfo.from_container(c) for c in containers]
    
    @docker_operation("cleanup_stopped")
    async def cleanup_stopped_containers(self) -> int:
        """Remove all stopped workspace containers.
        
        Returns:
            Number of containers removed
        """
        containers = await self.list_containers(include_stopped=True)
        removed = 0
        
        for container in containers:
            if container.status != ContainerStatus.RUNNING:
                try:
                    c = self.client.containers.get(container.id)
                    await asyncio.to_thread(c.remove, force=True)
                    removed += 1
                except:
                    pass
        
        return removed
    
    @docker_operation("ensure_image_exists")
    async def ensure_image_exists(self, pull_if_missing: bool = True) -> bool:
        """Ensure workspace Docker image exists.
        
        Args:
            pull_if_missing: Whether to pull image if not found locally
            
        Returns:
            True if image exists or was pulled
        """
        try:
            await asyncio.to_thread(
                self.client.images.get,
                self._config.image,
            )
            return True
        except ImageNotFound:
            if pull_if_missing:
                try:
                    await asyncio.to_thread(
                        self.client.images.pull,
                        self._config.image,
                    )
                    return True
                except:
                    return False
            return False
    
    @docker_operation("build_workspace_image")
    async def build_workspace_image(
        self, 
        dockerfile_path: str,
        tag: Optional[str] = None,
    ) -> bool:
        """Build workspace Docker image.
        
        Args:
            dockerfile_path: Path to Dockerfile
            tag: Image tag (uses config image if not provided)
            
        Returns:
            True if built successfully
        """
        dockerfile_dir = str(Path(dockerfile_path).parent)
        image_tag = tag or self._config.image
        
        try:
            image, logs = await asyncio.to_thread(
                self.client.images.build,
                path=dockerfile_dir,
                tag=image_tag,
                rm=True,
            )
            return True
        except Exception as e:
            raise DockerError(
                message=f"Failed to build image: {e}",
                operation="build_image",
            )
    
    @docker_operation("get_container_logs")
    async def get_container_logs(
        self,
        session_id: str,
        tail: int = 100,
        since: Optional[datetime] = None,
    ) -> str:
        """Get container logs.
        
        Args:
            session_id: Session identifier
            tail: Number of lines from the end
            since: Only logs since this time
            
        Returns:
            Log content as string
        """
        container_name = self._get_container_name(session_id)
        
        try:
            container = self.client.containers.get(container_name)
            kwargs = {"tail": tail}
            if since:
                kwargs["since"] = since
            
            logs = await asyncio.to_thread(
                container.logs,
                **kwargs,
            )
            return logs.decode() if isinstance(logs, bytes) else logs
        except NotFound:
            raise ContainerNotFoundError(
                message=f"Container not found: {container_name}",
                operation="get_logs",
            )
    
    async def cleanup_all(self, force: bool = True):
        """Cleanup all workspace containers.
        
        Args:
            force: Force removal of running containers
        """
        containers = await self.list_containers(include_stopped=True)
        
        for container in containers:
            try:
                c = self.client.containers.get(container.id)
                await asyncio.to_thread(c.remove, force=force)
            except:
                pass


# Global Docker service instance
docker_service = DockerService()
