# -*- coding: utf-8 -*-
"""
Constants for sandbox executor.

Note: Most configuration values are now loaded from ExecutorConfig in settings.py.
These constants provide defaults and fixed values.
"""

# Container owner identifier for filtering
CONTAINER_OWNER = "coding_assistant_sandbox"

# Docker socket path
DOCKER_SOCKET_PATH = "/var/run/docker.sock"

# API endpoints on the executor container
DEFAULT_API_ENDPOINT = "/api/tasks/execute"
DEFAULT_STREAM_ENDPOINT = "/api/tasks/stream"
DEFAULT_CANCEL_ENDPOINT = "/api/tasks/cancel"
DEFAULT_HEALTH_ENDPOINT = "/health"

# Environment configuration
DEFAULT_TIMEZONE = "Asia/Shanghai"
DEFAULT_LOCALE = "en_US.UTF-8"

# Mount paths
WORKSPACE_MOUNT_PATH = "/workspace"

# ============================================================================
# Container internal ports (fixed)
# ============================================================================
INTERNAL_API_PORT = 8080       # FastAPI executor service inside container
INTERNAL_CODE_PORT = 3000      # Repo Server inside container

# ============================================================================
# Default values (can be overridden by ExecutorConfig)
# ============================================================================
DEFAULT_DOCKER_HOST = "host.docker.internal"
DEFAULT_EXECUTOR_IMAGE = "coding-assistant-executor:latest"
DEFAULT_MEMORY_LIMIT = "4g"
DEFAULT_CPU_COUNT = 2
HEALTH_CHECK_TIMEOUT = 30

