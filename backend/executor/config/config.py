# -*- coding: utf-8 -*-
"""
Executor configuration management.

Configuration values are passed from the main backend via environment variables.
"""

import os
import json
from typing import Dict, Any, Optional, List

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
    "WebFetch",
]

# =============================================================================
# Playwright MCP Tools
# =============================================================================
# Reference: https://github.com/anthropics/claude-quickstarts/blob/main/autonomous-coding/client.py
# Full list of Playwright MCP tools for browser automation
PLAYWRIGHT_MCP_TOOLS = [
    # Navigation
    "mcp__playwright__browser_navigate",
    "mcp__playwright__browser_navigate_back",
    "mcp__playwright__browser_navigate_forward",
    # Page interaction
    "mcp__playwright__browser_click",
    "mcp__playwright__browser_type",
    "mcp__playwright__browser_fill",
    "mcp__playwright__browser_select_option",
    "mcp__playwright__browser_hover",
    "mcp__playwright__browser_drag",
    "mcp__playwright__browser_press_key",
    # Page state
    "mcp__playwright__browser_snapshot",
    "mcp__playwright__browser_take_screenshot",
    "mcp__playwright__browser_get_text",
    "mcp__playwright__browser_get_html",
    # Browser management
    "mcp__playwright__browser_wait_for",
    "mcp__playwright__browser_resize",
    "mcp__playwright__browser_close",
    "mcp__playwright__browser_install",
    # Tab management
    "mcp__playwright__browser_tab_list",
    "mcp__playwright__browser_tab_new",
    "mcp__playwright__browser_tab_select",
    "mcp__playwright__browser_tab_close",
    # Advanced
    "mcp__playwright__browser_console_messages",
    "mcp__playwright__browser_network_requests",
    "mcp__playwright__browser_file_upload",
    "mcp__playwright__browser_pdf_save",
    "mcp__playwright__browser_handle_dialog",
    "mcp__playwright__browser_generate_playwright_test",
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

# =============================================================================
# Default MCP Servers Configuration
# =============================================================================
# MCP servers are automatically loaded when creating Claude agent options.
# Use get_mcp_servers() to get the active configuration.

# Default MCP servers (commonly used ones)
DEFAULT_MCP_SERVERS: Dict[str, Any] = {
    # Playwright for browser automation (headless mode for container environment)
    # Uses globally installed mcp-server-playwright command
    # --headless: Run browser in headless mode
    # --isolated: Keep browser profile in memory, avoid disk lock issues
    # --no-sandbox: Required for running in Docker container as root
    "playwright": {
        "command": "mcp-server-playwright",
        "args": ["--headless", "--isolated", "--no-sandbox"],
    },
}

# Alternative: Use npx to run playwright MCP (downloads on first use)
NPX_MCP_SERVERS: Dict[str, Any] = {
    "playwright": {
        "command": "npx",
        "args": ["@playwright/mcp@latest", "--headless", "--isolated", "--no-sandbox"],
    },
}

def get_default_mcp_tools() -> List[str]:
    """Get default MCP tools based on configured servers."""
    tools = []
    # Add Playwright tools by default
    tools.extend(PLAYWRIGHT_MCP_TOOLS)
    return tools

def get_all_default_tools() -> List[str]:
    """Get all default tools including MCP tools."""
    return DEFAULT_TOOLS + get_default_mcp_tools()

