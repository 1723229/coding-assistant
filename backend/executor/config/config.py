# -*- coding: utf-8 -*-
"""
Executor configuration management.

Configuration values are passed from the main backend via environment variables.
"""

import os
import json
from typing import Dict, Any, Optional

# Workspace root directory inside container
WORKSPACE_ROOT = os.environ.get("WORKSPACE_ROOT", "/workspace/")

# Server port (internal port inside container, default 8080)
PORT = int(os.environ.get("PORT", "8080"))

# Claude SDK configuration
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL")

# Disable experimental betas for API proxy compatibility
# This fixes "ip:port Extra inputs are not permitted" error with some proxies
CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS = os.environ.get("CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS", "1")

# Permission mode for Claude Code
PERMISSION_MODE = os.environ.get("PERMISSION_MODE", "bypassPermissions")

# Default tools for Claude Code
DEFAULT_TOOLS = [
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
]

# Session timeout in seconds
SESSION_TIMEOUT = int(os.environ.get("SESSION_TIMEOUT", "1800"))

# Task cancellation configuration
CANCEL_TIMEOUT_SECONDS = int(os.environ.get("CANCEL_TIMEOUT_SECONDS", "30"))

# MCP Server configuration
# Can be set via environment variable MCP_SERVERS as JSON string
# Or loaded from .mcp.json file in workspace
MCP_SERVERS_JSON = os.environ.get("MCP_SERVERS", "")

def get_mcp_servers_from_env() -> Dict[str, Any]:
    """Get MCP servers configuration from environment variable."""
    if MCP_SERVERS_JSON:
        try:
            return json.loads(MCP_SERVERS_JSON)
        except json.JSONDecodeError:
            return {}
    return {}

def get_mcp_servers_from_file(workspace_path: str) -> Dict[str, Any]:
    """Load MCP servers configuration from .mcp.json file in workspace."""
    mcp_file = os.path.join(workspace_path, ".mcp.json")
    if os.path.exists(mcp_file):
        try:
            with open(mcp_file, "r") as f:
                config = json.load(f)
                return config.get("mcpServers", {})
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def get_mcp_servers(workspace_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Get MCP servers configuration.
    
    Priority:
    1. Environment variable MCP_SERVERS (JSON string)
    2. .mcp.json file in workspace
    
    Args:
        workspace_path: Optional workspace path to look for .mcp.json
        
    Returns:
        Dictionary of MCP server configurations
    """
    # First try environment variable
    servers = get_mcp_servers_from_env()
    if servers:
        return servers
    
    # Then try workspace file
    if workspace_path:
        servers = get_mcp_servers_from_file(workspace_path)
        if servers:
            return servers
    
    return {}

# Default MCP servers (commonly used ones)
DEFAULT_MCP_SERVERS: Dict[str, Any] = {
    # Playwright for browser automation
    "playwright": {
        "command": "npx",
        "args": ["@playwright/mcp@latest"],
    },
}

