# -*- coding: utf-8 -*-
"""
Executor module for sandbox container management.

This module provides:
- Container lifecycle management (create, start, stop, remove)
- Task execution via container API
- SSE stream proxying from container to client
"""

from app.core.executor.base import ExecutorBase, ExecutorError
from app.core.executor.docker_executor import SandboxDockerExecutor, get_sandbox_executor
from app.core.executor.container_manager import ContainerManager, get_container_manager
from app.core.executor.stream_proxy import StreamProxy
from app.core.executor.constants import (
    CONTAINER_OWNER,
    DEFAULT_DOCKER_HOST,
    DEFAULT_API_ENDPOINT,
    DEFAULT_STREAM_ENDPOINT,
    WORKSPACE_MOUNT_PATH,
    DEFAULT_EXECUTOR_IMAGE,
)

__all__ = [
    "ExecutorBase",
    "ExecutorError",
    "SandboxDockerExecutor",
    "get_sandbox_executor",
    "ContainerManager",
    "get_container_manager",
    "StreamProxy",
    "CONTAINER_OWNER",
    "DEFAULT_DOCKER_HOST",
    "DEFAULT_API_ENDPOINT",
    "DEFAULT_STREAM_ENDPOINT",
    "WORKSPACE_MOUNT_PATH",
    "DEFAULT_EXECUTOR_IMAGE",
]

