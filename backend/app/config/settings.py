"""
Configuration Module

Provides centralized configuration management for the application.
Supports YAML config files following employee-platform pattern.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from functools import lru_cache
from pydantic_settings import BaseSettings


def load_yaml_config() -> Dict[str, Any]:
    """
    Load configuration from YAML file
    
    Returns:
        Dictionary containing all configuration values
    """
    config_dir = Path(__file__).parent
    config_path = config_dir / "config.yaml"

    if not config_path.exists():
        # Fallback to example config if main config doesn't exist
        config_path = config_dir / "config.example.yaml"
        if not config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found. Please create {config_dir / 'config.yaml'} "
                f"based on {config_dir / 'config.example.yaml'}"
            )

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML configuration: {e}")
    except Exception as e:
        raise RuntimeError(f"Error loading configuration file: {e}")


# Load configuration
_config = load_yaml_config()


# ============================================================================
# Database Configuration
# ============================================================================

class DatabaseConfig:
    """Database configuration management"""

    _db_config = _config.get("database", {})

    # Database connection parameters
    HOST = _db_config.get("host", "localhost")
    PORT = _db_config.get("port", 3306)
    USER = _db_config.get("user", "root")
    PASSWORD = _db_config.get("password", "")
    NAME = _db_config.get("name", "coding_assistant")
    CHARSET = _db_config.get("charset", "utf8mb4")

    # Connection pool settings
    POOL_SIZE = _db_config.get("pool_size", 10)
    MAX_OVERFLOW = _db_config.get("max_overflow", 20)
    POOL_RECYCLE = _db_config.get("pool_recycle", 3600)

    # Connection timeout settings
    CONNECT_TIMEOUT = _db_config.get("connect_timeout", 60)
    READ_TIMEOUT = _db_config.get("read_timeout", 60)
    WRITE_TIMEOUT = _db_config.get("write_timeout", 60)

    @classmethod
    def get_database_url(cls) -> str:
        """
        Build MySQL database connection URL

        Returns:
            Complete database connection URL
        """
        return f"mysql+pymysql://{cls.USER}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{cls.NAME}"

    @classmethod
    def get_async_database_url(cls) -> str:
        """
        Build async MySQL database connection URL

        Returns:
            Complete async database connection URL
        """
        return f"mysql+aiomysql://{cls.USER}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{cls.NAME}"


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

    @classmethod
    def get_web_interface_url(cls) -> str:
        """
        Get Web interface URL
        
        Returns:
            Complete Web interface URL
        """
        return f"http://localhost:{cls.PORT}"


# ============================================================================
# Claude Configuration
# ============================================================================

class ClaudeConfig:
    """Claude SDK configuration management"""

    _claude_config = _config.get("claude", {})

    # API Settings
    API_KEY = _claude_config.get("api_key")
    BASE_URL = _claude_config.get("base_url")

    # Model selection
    MODEL = _claude_config.get("model")

    # Default tools
    DEFAULT_TOOLS = _claude_config.get("default_tools", [
        "Read",
        "Write",
        "Edit",
        "MultiEdit",
        "Bash",
        "Glob",
        "Grep",
        "LS",
        "TodoRead",
        "TodoWrite",
    ])

    # Permission mode
    PERMISSION_MODE = _claude_config.get("permission_mode", "acceptEdits")

    # Session settings
    SESSION_TIMEOUT = _claude_config.get("session_timeout", 1800)  # 30 minutes

    @classmethod
    def setup_environment(cls):
        """Set up environment variables for Claude SDK"""
        if cls.API_KEY:
            os.environ["ANTHROPIC_API_KEY"] = cls.API_KEY
        if cls.BASE_URL:
            os.environ["ANTHROPIC_BASE_URL"] = cls.BASE_URL
        print("Anthropic API key:", os.environ["ANTHROPIC_API_KEY"])
        print("Base URL:", os.environ["ANTHROPIC_BASE_URL"])


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
# Docker Configuration
# ============================================================================

class DockerConfig:
    """Docker configuration management"""

    _docker_config = _config.get("docker", {})

    IMAGE = _docker_config.get("image", "claude-workspace:latest")
    NETWORK = _docker_config.get("network", "claude-network")
    MEMORY_LIMIT = _docker_config.get("memory_limit", "2g")
    CPU_QUOTA = _docker_config.get("cpu_quota", 100000)


# ============================================================================
# Pydantic Settings (for backward compatibility and validation)
# ============================================================================

class Settings(BaseSettings):
    """Application settings with validation"""

    # Application
    app_name: str = "Claude Code Web Platform"
    debug: bool = ServerConfig.DEBUG

    # API Configuration
    anthropic_api_key: str = ClaudeConfig.API_KEY
    anthropic_base_url: str = ClaudeConfig.BASE_URL
    anthropic_model: str = ClaudeConfig.MODEL

    # GitHub Configuration
    github_token: str = GitHubConfig.TOKEN
    github_default_repo: str = GitHubConfig.DEFAULT_REPO

    # Database
    database_url: str = DatabaseConfig.get_async_database_url()

    # Workspace Configuration
    workspace_base_path: Path = WorkspaceConfig.BASE_PATH

    # Docker Configuration
    docker_image: str = DockerConfig.IMAGE
    docker_network: str = DockerConfig.NETWORK

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
    # Setup Claude environment variables
    ClaudeConfig.setup_environment()
    # Ensure workspace exists
    WorkspaceConfig.ensure_exists()
    return Settings()


# ============================================================================
# Export all configs for easy import
# ============================================================================

__all__ = [
    "load_yaml_config",
    "DatabaseConfig",
    "ServerConfig",
    "ClaudeConfig",
    "GitHubConfig",
    "WorkspaceConfig",
    "DockerConfig",
    "Settings",
    "get_settings",
]
