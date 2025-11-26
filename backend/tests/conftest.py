"""Pytest configuration and fixtures for backend tests."""

import os
import sys
import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Generator, AsyncGenerator

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_workspace(tmp_path) -> Path:
    """Create a temporary workspace directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def mock_git_repo(temp_workspace):
    """Create a mock git repository."""
    from git import Repo
    
    repo = Repo.init(temp_workspace)
    
    # Create initial commit
    readme = temp_workspace / "README.md"
    readme.write_text("# Test Repo")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")
    
    return repo


@pytest.fixture
def mock_github_token():
    """Mock GitHub token for testing."""
    return "ghp_test_token_12345678901234567890"


@pytest.fixture
def mock_github_client():
    """Create mock GitHub client."""
    mock = MagicMock()
    mock.get_user.return_value = MagicMock(
        login="testuser",
        get_repos=MagicMock(return_value=[])
    )
    return mock


@pytest.fixture
def mock_docker_client():
    """Create mock Docker client."""
    mock = MagicMock()
    mock.ping.return_value = True
    mock.containers = MagicMock()
    mock.images = MagicMock()
    return mock


@pytest.fixture
def mock_claude_client():
    """Create mock Claude SDK client."""
    mock = AsyncMock()
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.query = AsyncMock()
    return mock


@pytest.fixture
def sample_repo_info():
    """Sample repository info for testing."""
    return {
        "name": "test-repo",
        "owner": "testuser",
        "full_name": "testuser/test-repo",
        "url": "https://github.com/testuser/test-repo.git",
        "default_branch": "main",
        "description": "A test repository",
        "is_private": False,
    }


@pytest.fixture
def sample_file_changes():
    """Sample file changes for testing."""
    return [
        {"path": "file1.py", "status": "added"},
        {"path": "file2.py", "status": "modified"},
        {"path": "file3.py", "status": "deleted"},
    ]


