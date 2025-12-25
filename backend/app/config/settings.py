"""
Configuration Module

Provides centralized configuration management for the application.
Supports YAML config files.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from functools import lru_cache
from pydantic_settings import BaseSettings


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries. Override values take precedence.

    Args:
        base: Base configuration dictionary
        override: Override configuration dictionary

    Returns:
        Merged configuration dictionary
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_yaml_config() -> Dict[str, Any]:
    """
    Load configuration from YAML files with local override support.

    Loading order:
    1. Load config.yaml (or config.example.yaml as fallback) as base configuration
    2. If config.local.yaml exists, merge it with base (local values override base)
    3. Return merged configuration

    This allows each developer to have their own local configuration without
    affecting the test/production environment's config.yaml.

    Returns:
        Dictionary containing all configuration values
    """
    config_dir = Path(__file__).parent
    config_path = config_dir / "config.yaml"

    # Load base configuration
    if not config_path.exists():
        config_path = config_dir / "config.example.yaml"
        if not config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found. Please create {config_dir / 'config.yaml'} "
                f"based on {config_dir / 'config.example.yaml'}"
            )

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            base_config = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML configuration: {e}")
    except Exception as e:
        raise RuntimeError(f"Error loading configuration file: {e}")

    # Load local configuration if exists
    local_config_path = config_dir / "config.local.yaml"
    if local_config_path.exists():
        try:
            with open(local_config_path, 'r', encoding='utf-8') as f:
                local_config = yaml.safe_load(f) or {}
            # Merge local config with base config (local overrides base)
            return deep_merge(base_config, local_config)
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing local YAML configuration: {e}")
        except Exception as e:
            raise RuntimeError(f"Error loading local configuration file: {e}")

    return base_config


# Load configuration
_config = load_yaml_config()


# ============================================================================
# Database Configuration
# ============================================================================

class DatabaseConfig:
    """Database configuration management"""

    _db_config = _config.get("database", {})

    HOST = _db_config.get("host", "localhost")
    PORT = _db_config.get("port", 3306)
    USER = _db_config.get("user", "root")
    PASSWORD = _db_config.get("password", "")
    NAME = _db_config.get("name", "coding_assistant")
    CHARSET = _db_config.get("charset", "utf8mb4")

    POOL_SIZE = _db_config.get("pool_size", 10)
    MAX_OVERFLOW = _db_config.get("max_overflow", 20)
    POOL_RECYCLE = _db_config.get("pool_recycle", 3600)

    CONNECT_TIMEOUT = _db_config.get("connect_timeout", 60)
    READ_TIMEOUT = _db_config.get("read_timeout", 60)
    WRITE_TIMEOUT = _db_config.get("write_timeout", 60)

    @classmethod
    def get_database_url(cls) -> str:
        return f"mysql+pymysql://{cls.USER}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{cls.NAME}"

    @classmethod
    def get_async_database_url(cls) -> str:
        return f"mysql+aiomysql://{cls.USER}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{cls.NAME}"


# ============================================================================
# Framework Database Configuration
# ============================================================================

class FrameworkDatabaseConfig:
    """Framework database configuration (for sys_module table)"""

    _framework_db_config = _config.get("framework_database", {})

    HOST = _framework_db_config.get("host", "localhost")
    PORT = _framework_db_config.get("port", 3306)
    USER = _framework_db_config.get("user", "root")
    PASSWORD = _framework_db_config.get("password", "")
    DATABASE = _framework_db_config.get("database", "framework")


# ============================================================================
# Server Configuration
# ============================================================================

class ServerConfig:
    """Server configuration management"""

    _server_config = _config.get("server", {})

    HOST = _server_config.get("host", "0.0.0.0")
    PORT = _server_config.get("port", 8000)
    RELOAD = _server_config.get("reload", True)
    DEBUG = _server_config.get("debug", False)
    CORS_ORIGINS = _server_config.get("cors_origins", ["http://localhost:5173", "http://localhost:3000"])
    PREVIEW_IP = _server_config.get("preview_ip", "http://locaalhost")

    @classmethod
    def get_web_interface_url(cls) -> str:
        return f"http://localhost:{cls.PORT}"


# ============================================================================
# GitHub Configuration
# ============================================================================

class GitHubConfig:
    """GitHub configuration management"""

    _github_config = _config.get("github", {})

    TOKEN = os.environ.get("GITHUB_TOKEN") or _github_config.get("token", "")
    DEFAULT_REPO = _github_config.get("default_repo", "")


# ============================================================================
# Workspace Configuration
# ============================================================================

class WorkspaceConfig:
    """Workspace configuration management"""

    _workspace_config = _config.get("workspace", {})

    BASE_PATH = Path(_workspace_config.get("base_path", "./workspaces"))

    @classmethod
    def ensure_exists(cls):
        """Ensure workspace directory exists"""
        cls.BASE_PATH.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Project Configuration
# ============================================================================

class ProjectConfig:
    """Project configuration for default values"""

    _project_config = _config.get("project", {})

    DEFAULT_CODEBASE = _project_config.get("default_codebase", "")
    DEFAULT_TOKEN = _project_config.get("default_token", "")


# ============================================================================
# Docker Configuration (Legacy - for workspace containers)
# ============================================================================

class DockerConfig:
    """Docker configuration for workspace containers (legacy)"""

    _docker_config = _config.get("docker", {})

    IMAGE = _docker_config.get("image", "claude-workspace:latest")
    NETWORK = _docker_config.get("network", "claude-network")
    MEMORY_LIMIT = _docker_config.get("memory_limit", "2g")
    CPU_QUOTA = _docker_config.get("cpu_quota", 100000)


# ============================================================================
# Executor Configuration (Sandbox Mode)
# ============================================================================

class ExecutorConfig:
    """Executor configuration for sandbox containers"""

    _executor_config = _config.get("executor", {})

    # Docker image for executor containers
    IMAGE = _executor_config.get("image", "coding-assistant-executor:latest")
    
    # Port range for executor containers (API service)
    API_PORT_RANGE_MIN = _executor_config.get("api_port_range_min", 10001)
    API_PORT_RANGE_MAX = _executor_config.get("api_port_range_max", 10100)
    
    # Port range for code service
    CODE_PORT_RANGE_MIN = _executor_config.get("code_port_range_min", 20001)
    CODE_PORT_RANGE_MAX = _executor_config.get("code_port_range_max", 20100)
    
    # Timeouts in seconds
    REQUEST_TIMEOUT = _executor_config.get("request_timeout", 300)
    STREAM_TIMEOUT = _executor_config.get("stream_timeout", 6000)
    HEALTH_CHECK_TIMEOUT = _executor_config.get("health_check_timeout", 30)
    
    # Container resource limits
    MEMORY_LIMIT = _executor_config.get("container_memory", "4g")
    CPU_COUNT = _executor_config.get("container_cpu", 2)
    
    # Docker host address (for container-to-host communication)
    DOCKER_HOST = _executor_config.get("docker_host", "host.docker.internal")
    
    # Session timeout
    SESSION_TIMEOUT = _executor_config.get("session_timeout", 1800)
    
    # Claude API Configuration (passed to sandbox containers)
    ANTHROPIC_API_KEY = _executor_config.get("anthropic_api_key", "")
    ANTHROPIC_BASE_URL = _executor_config.get("anthropic_base_url", "")
    ANTHROPIC_MODEL = _executor_config.get("anthropic_model", "claude-sonnet-4-20250514")


# ============================================================================
# Container Management Configuration
# ============================================================================

class ContainerConfig:
    """Container management configuration"""

    _container_config = _config.get("container", {})

    MAX_RUNNING_CONTAINERS = _container_config.get("max_running_containers", 1)


# ============================================================================
# Pydantic Settings
# ============================================================================

class Settings(BaseSettings):
    """Application settings with validation"""

    # Application
    app_name: str = "Coding Assistant"
    debug: bool = ServerConfig.DEBUG

    # GitHub Configuration
    github_token: str = GitHubConfig.TOKEN
    github_default_repo: str = GitHubConfig.DEFAULT_REPO

    # LOCAL_IP
    server_ip: str = ServerConfig.HOST

    preview_ip: str = ServerConfig.PREVIEW_IP

    # Database
    database_url: str = DatabaseConfig.get_async_database_url()

    # Workspace Configuration
    workspace_base_path: Path = WorkspaceConfig.BASE_PATH

    # Docker Configuration (Legacy - for workspace containers)
    docker_image: str = DockerConfig.IMAGE
    docker_network: str = DockerConfig.NETWORK
    docker_memory_limit: str = DockerConfig.MEMORY_LIMIT
    docker_cpu_quota: int = DockerConfig.CPU_QUOTA

    # Executor Configuration (Sandbox Mode)
    executor_image: str = ExecutorConfig.IMAGE
    executor_api_port_range_min: int = ExecutorConfig.API_PORT_RANGE_MIN
    executor_api_port_range_max: int = ExecutorConfig.API_PORT_RANGE_MAX
    executor_code_port_range_min: int = ExecutorConfig.CODE_PORT_RANGE_MIN
    executor_code_port_range_max: int = ExecutorConfig.CODE_PORT_RANGE_MAX
    executor_request_timeout: int = ExecutorConfig.REQUEST_TIMEOUT
    executor_stream_timeout: int = ExecutorConfig.STREAM_TIMEOUT
    executor_memory_limit: str = ExecutorConfig.MEMORY_LIMIT
    executor_cpu_count: int = ExecutorConfig.CPU_COUNT

    # Server
    host: str = ServerConfig.HOST
    port: int = ServerConfig.PORT
    cors_origins: List[str] = ServerConfig.CORS_ORIGINS

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    # Ensure workspace exists
    WorkspaceConfig.ensure_exists()
    return Settings()


# ============================================================================
# Export all configs for easy import
# ============================================================================

__all__ = [
    "load_yaml_config",
    "DatabaseConfig",
    "FrameworkDatabaseConfig",
    "ServerConfig",
    "GitHubConfig",
    "WorkspaceConfig",
    "DockerConfig",
    "ExecutorConfig",
    "ContainerConfig",
    "Settings",
    "get_settings",
]
