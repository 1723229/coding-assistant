"""Application configuration management."""

import os
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "Claude Code Web Platform"
    debug: bool = False
    
    # API Configuration
    anthropic_api_key: str = "sk-ww6QLSsRmcFO2mUQHFKqll35xJe4jCqwqDFqTShWIccudM2g"
    anthropic_base_url: str = "https://api.moonshot.cn/anthropic/"
    
    # GitHub Configuration
    github_token: str = ""
    github_default_repo: str = ""
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    
    # Workspace Configuration
    workspace_base_path: Path = Path("./workspaces")
    
    # Docker Configuration
    docker_image: str = "claude-workspace:latest"
    docker_network: str = "claude-network"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Create workspace directory if it doesn't exist
settings = get_settings()
settings.workspace_base_path.mkdir(parents=True, exist_ok=True)

# Create data directory for database
Path("./data").mkdir(parents=True, exist_ok=True)

