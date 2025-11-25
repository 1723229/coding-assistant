"""Docker container management service for workspace isolation."""

import os
import asyncio
from typing import Optional
from pathlib import Path
from dataclasses import dataclass

import docker
from docker.models.containers import Container
from docker.errors import NotFound, APIError

from ..config import get_settings

settings = get_settings()


@dataclass
class ContainerInfo:
    """Container information."""
    id: str
    name: str
    status: str
    workspace_path: str


class DockerService:
    """Service for managing Docker workspace containers."""
    
    def __init__(self):
        """Initialize Docker client."""
        self._client: Optional[docker.DockerClient] = None
        
    @property
    def client(self) -> docker.DockerClient:
        """Get Docker client, creating if needed."""
        if self._client is None:
            self._client = docker.from_env()
        return self._client
    
    def _get_container_name(self, session_id: str) -> str:
        """Get container name for session."""
        return f"claude-workspace-{session_id[:8]}"
    
    async def create_workspace(
        self,
        session_id: str,
        workspace_path: str,
    ) -> ContainerInfo:
        """Create a workspace container for a session.
        
        Args:
            session_id: Session identifier
            workspace_path: Host path to mount as workspace
            
        Returns:
            ContainerInfo with container details
        """
        container_name = self._get_container_name(session_id)
        
        # Ensure workspace directory exists
        Path(workspace_path).mkdir(parents=True, exist_ok=True)
        
        # Check if container already exists
        try:
            existing = self.client.containers.get(container_name)
            if existing.status != "running":
                existing.start()
            return ContainerInfo(
                id=existing.id,
                name=container_name,
                status=existing.status,
                workspace_path=workspace_path,
            )
        except NotFound:
            pass
        
        # Create new container
        container = await asyncio.to_thread(
            self._create_container,
            container_name,
            workspace_path,
        )
        
        return ContainerInfo(
            id=container.id,
            name=container_name,
            status=container.status,
            workspace_path=workspace_path,
        )
    
    def _create_container(
        self,
        container_name: str,
        workspace_path: str,
    ) -> Container:
        """Create Docker container (sync helper)."""
        abs_workspace = str(Path(workspace_path).resolve())
        
        container = self.client.containers.run(
            image=settings.docker_image,
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
            environment={
                "WORKSPACE_PATH": "/workspace",
            },
            # Resource limits
            mem_limit="2g",
            cpu_period=100000,
            cpu_quota=100000,  # 1 CPU
            # Network
            network_mode=settings.docker_network if settings.docker_network else None,
            # Auto-remove on stop
            auto_remove=False,
        )
        
        return container
    
    async def execute_command(
        self,
        session_id: str,
        command: str,
        workdir: Optional[str] = None,
    ) -> tuple[int, str]:
        """Execute command in workspace container.
        
        Args:
            session_id: Session identifier
            command: Command to execute
            workdir: Working directory inside container
            
        Returns:
            Tuple of (exit_code, output)
        """
        container_name = self._get_container_name(session_id)
        
        try:
            container = self.client.containers.get(container_name)
        except NotFound:
            return (1, f"Container not found: {container_name}")
        
        if container.status != "running":
            container.start()
        
        # Execute command
        result = await asyncio.to_thread(
            container.exec_run,
            command,
            workdir=workdir or "/workspace",
            demux=True,
        )
        
        exit_code = result.exit_code
        stdout = result.output[0].decode() if result.output[0] else ""
        stderr = result.output[1].decode() if result.output[1] else ""
        
        output = stdout + stderr
        return (exit_code, output)
    
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
            # Get workspace path from mounts
            workspace_path = ""
            for mount in container.attrs.get("Mounts", []):
                if mount.get("Destination") == "/workspace":
                    workspace_path = mount.get("Source", "")
                    break
                    
            return ContainerInfo(
                id=container.id,
                name=container_name,
                status=container.status,
                workspace_path=workspace_path,
            )
        except NotFound:
            return None
    
    async def stop_container(self, session_id: str) -> bool:
        """Stop workspace container.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if stopped, False if not found
        """
        container_name = self._get_container_name(session_id)
        
        try:
            container = self.client.containers.get(container_name)
            container.stop(timeout=10)
            return True
        except NotFound:
            return False
    
    async def remove_container(self, session_id: str, force: bool = False) -> bool:
        """Remove workspace container.
        
        Args:
            session_id: Session identifier
            force: Force removal even if running
            
        Returns:
            True if removed, False if not found
        """
        container_name = self._get_container_name(session_id)
        
        try:
            container = self.client.containers.get(container_name)
            container.remove(force=force)
            return True
        except NotFound:
            return False
    
    async def list_containers(self) -> list[ContainerInfo]:
        """List all workspace containers.
        
        Returns:
            List of ContainerInfo
        """
        containers = self.client.containers.list(
            all=True,
            filters={"name": "claude-workspace-"},
        )
        
        result = []
        for container in containers:
            workspace_path = ""
            for mount in container.attrs.get("Mounts", []):
                if mount.get("Destination") == "/workspace":
                    workspace_path = mount.get("Source", "")
                    break
                    
            result.append(ContainerInfo(
                id=container.id,
                name=container.name,
                status=container.status,
                workspace_path=workspace_path,
            ))
        
        return result
    
    async def ensure_image_exists(self) -> bool:
        """Ensure workspace Docker image exists.
        
        Returns:
            True if image exists or was built
        """
        try:
            self.client.images.get(settings.docker_image)
            return True
        except NotFound:
            # Image doesn't exist, would need to build it
            return False
    
    async def build_workspace_image(self, dockerfile_path: str) -> bool:
        """Build workspace Docker image.
        
        Args:
            dockerfile_path: Path to Dockerfile
            
        Returns:
            True if built successfully
        """
        try:
            dockerfile_dir = str(Path(dockerfile_path).parent)
            image, logs = await asyncio.to_thread(
                self.client.images.build,
                path=dockerfile_dir,
                tag=settings.docker_image,
                rm=True,
            )
            return True
        except Exception as e:
            print(f"Failed to build image: {e}")
            return False


# Global Docker service instance
docker_service = DockerService()

