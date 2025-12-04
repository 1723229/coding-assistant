# -*- coding: utf-8 -*-
"""
Executor configuration management.

Configuration values are passed from the main backend via environment variables.
"""

import os

# Workspace root directory inside container
WORKSPACE_ROOT = os.environ.get("WORKSPACE_ROOT", "/workspace/")

# Server port (internal port inside container, default 8080)
PORT = int(os.environ.get("PORT", "8080"))

# Claude SDK configuration
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "sk-e43189bfbcc24a01bab723f9ebb38e81")
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://dashscope.aliyuncs.com/apps/anthropic")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "qwen3-coder-plus")

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

