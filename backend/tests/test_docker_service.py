"""Tests for Docker service."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.docker_service import (
    DockerService,
    ContainerInfo,
    ContainerStatus,
    ContainerConfig,
    ExecutionResult,
    DockerError,
    ContainerNotFoundError,
    ContainerExecutionError,
)


class TestContainerStatus:
    """Tests for ContainerStatus enum."""
    
    def test_status_values(self):
        """Test status enum values."""
        assert ContainerStatus.RUNNING.value == "running"
        assert ContainerStatus.STOPPED.value == "stopped"
        assert ContainerStatus.EXITED.value == "exited"
        assert ContainerStatus.UNKNOWN.value == "unknown"


class TestContainerConfig:
    """Tests for ContainerConfig dataclass."""
    
    def test_default_config(self):
        """Test default container configuration."""
        config = ContainerConfig()
        
        assert config.memory_limit == "2g"
        assert config.cpu_quota == 100000
        assert config.cpu_period == 100000
        assert config.auto_remove is False
    
    def test_custom_config(self):
        """Test custom container configuration."""
        config = ContainerConfig(
            image="custom-image:latest",
            memory_limit="4g",
            cpu_quota=200000,
            environment={"MY_VAR": "value"},
        )
        
        assert config.image == "custom-image:latest"
        assert config.memory_limit == "4g"
        assert config.cpu_quota == 200000
        assert config.environment["MY_VAR"] == "value"


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""
    
    def test_successful_result(self):
        """Test successful execution result."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Hello, world!",
            stderr="",
        )
        
        assert result.success is True
        assert result.output == "Hello, world!"
    
    def test_failed_result(self):
        """Test failed execution result."""
        result = ExecutionResult(
            exit_code=1,
            stdout="",
            stderr="Error: command not found",
        )
        
        assert result.success is False
        assert result.output == "Error: command not found"
    
    def test_combined_output(self):
        """Test combined stdout and stderr."""
        result = ExecutionResult(
            exit_code=0,
            stdout="Output: ",
            stderr="Warning: deprecated",
        )
        
        assert result.output == "Output: Warning: deprecated"


class TestContainerInfo:
    """Tests for ContainerInfo dataclass."""
    
    def test_create_container_info(self):
        """Test creating ContainerInfo."""
        info = ContainerInfo(
            id="abc123",
            name="test-container",
            status=ContainerStatus.RUNNING,
            workspace_path="/tmp/workspace",
        )
        
        assert info.id == "abc123"
        assert info.name == "test-container"
        assert info.status == ContainerStatus.RUNNING
        assert info.workspace_path == "/tmp/workspace"
    
    def test_from_container(self):
        """Test creating ContainerInfo from Docker container."""
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.name = "test-container"
        mock_container.status = "running"
        mock_container.attrs = {
            "Created": "2024-01-01T00:00:00.000000Z",
            "Mounts": [
                {"Destination": "/workspace", "Source": "/host/path"}
            ]
        }
        
        info = ContainerInfo.from_container(mock_container)
        
        assert info.id == "abc123"
        assert info.name == "test-container"
        assert info.status == ContainerStatus.RUNNING
        assert info.workspace_path == "/host/path"
    
    def test_from_container_unknown_status(self):
        """Test handling unknown status."""
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.name = "test-container"
        mock_container.status = "unknown_status"
        mock_container.attrs = {}
        
        info = ContainerInfo.from_container(mock_container)
        
        assert info.status == ContainerStatus.UNKNOWN


class TestDockerService:
    """Tests for DockerService class."""
    
    def test_init(self):
        """Test service initialization."""
        service = DockerService()
        
        assert service._client is None
        assert service._config is not None
    
    def test_init_with_config(self):
        """Test initialization with custom config."""
        config = ContainerConfig(memory_limit="4g")
        service = DockerService(config=config)
        
        assert service._config.memory_limit == "4g"
    
    def test_get_container_name(self):
        """Test container name generation."""
        service = DockerService()
        
        name = service._get_container_name("session-12345678-abcd")
        
        assert name == "claude-workspace-session-"
    
    def test_get_container_name_short_id(self):
        """Test container name with short session ID."""
        service = DockerService()
        
        name = service._get_container_name("abc")
        
        assert name == "claude-workspace-abc"
    
    @pytest.mark.asyncio
    async def test_check_docker_available(self, mock_docker_client):
        """Test checking Docker availability."""
        service = DockerService()
        service._client = mock_docker_client
        
        result = await service.check_docker_available()
        
        assert result is True
        mock_docker_client.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_docker_unavailable(self):
        """Test when Docker is unavailable."""
        service = DockerService()
        mock_client = MagicMock()
        mock_client.ping.side_effect = Exception("Docker not running")
        service._client = mock_client
        
        result = await service.check_docker_available()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_container_status_not_found(self, mock_docker_client):
        """Test getting status for non-existent container."""
        from docker.errors import NotFound
        
        mock_docker_client.containers.get.side_effect = NotFound("Not found")
        
        service = DockerService()
        service._client = mock_docker_client
        
        result = await service.get_container_status("non-existent")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_health_check_not_found(self, mock_docker_client):
        """Test health check for non-existent container."""
        from docker.errors import NotFound
        
        mock_docker_client.containers.get.side_effect = NotFound("Not found")
        
        service = DockerService()
        service._client = mock_docker_client
        
        result = await service.health_check("non-existent")
        
        assert result["healthy"] is False
        assert result["status"] == "not_found"
    
    @pytest.mark.asyncio
    async def test_list_containers_empty(self, mock_docker_client):
        """Test listing containers when none exist."""
        mock_docker_client.containers.list.return_value = []
        
        service = DockerService()
        service._client = mock_docker_client
        
        containers = await service.list_containers()
        
        assert containers == []
    
    @pytest.mark.asyncio
    async def test_list_containers(self, mock_docker_client):
        """Test listing containers."""
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.name = "claude-workspace-test"
        mock_container.status = "running"
        mock_container.attrs = {"Mounts": []}
        
        mock_docker_client.containers.list.return_value = [mock_container]
        
        service = DockerService()
        service._client = mock_docker_client
        
        containers = await service.list_containers()
        
        assert len(containers) == 1
        assert containers[0].id == "abc123"
    
    @pytest.mark.asyncio
    async def test_stop_container_not_found(self, mock_docker_client):
        """Test stopping non-existent container."""
        from docker.errors import NotFound
        
        mock_docker_client.containers.get.side_effect = NotFound("Not found")
        
        service = DockerService()
        service._client = mock_docker_client
        
        result = await service.stop_container("non-existent")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_remove_container_not_found(self, mock_docker_client):
        """Test removing non-existent container."""
        from docker.errors import NotFound
        
        mock_docker_client.containers.get.side_effect = NotFound("Not found")
        
        service = DockerService()
        service._client = mock_docker_client
        
        result = await service.remove_container("non-existent")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_ensure_image_exists(self, mock_docker_client):
        """Test checking if image exists."""
        mock_docker_client.images.get.return_value = MagicMock()
        
        service = DockerService()
        service._client = mock_docker_client
        
        result = await service.ensure_image_exists()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_ensure_image_exists_pull(self, mock_docker_client):
        """Test pulling image when not found."""
        from docker.errors import ImageNotFound
        
        mock_docker_client.images.get.side_effect = ImageNotFound("Not found")
        mock_docker_client.images.pull.return_value = MagicMock()
        
        service = DockerService()
        service._client = mock_docker_client
        
        result = await service.ensure_image_exists(pull_if_missing=True)
        
        assert result is True
        mock_docker_client.images.pull.assert_called_once()


class TestDockerError:
    """Tests for Docker exception classes."""
    
    def test_docker_error(self):
        """Test DockerError exception."""
        error = DockerError(
            message="Container failed",
            operation="create",
            details={"container_id": "abc123"},
        )
        
        assert str(error) == "Container failed"
        assert error.operation == "create"
        assert error.details["container_id"] == "abc123"
    
    def test_container_not_found_error(self):
        """Test ContainerNotFoundError exception."""
        error = ContainerNotFoundError(
            message="Container abc123 not found",
            operation="get_status",
        )
        
        assert str(error) == "Container abc123 not found"
        assert error.operation == "get_status"
    
    def test_container_execution_error(self):
        """Test ContainerExecutionError exception."""
        error = ContainerExecutionError(
            message="Command failed",
            operation="execute",
            details={"exit_code": 1},
        )
        
        assert str(error) == "Command failed"
        assert error.details["exit_code"] == 1



