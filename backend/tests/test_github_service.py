"""Tests for GitHub service."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from app.service.github_service import (
    GitHubService,
    RepoInfo,
    FileChange,
    PullRequestInfo,
    BranchInfo,
    GitOperationError,
    GitHubAPIError,
    parse_github_url,
)


class TestParseGitHubUrl:
    """Tests for parse_github_url function."""
    
    def test_parse_https_url(self):
        """Test parsing HTTPS URL."""
        owner, name = parse_github_url("https://github.com/owner/repo")
        assert owner == "owner"
        assert name == "repo"
    
    def test_parse_https_url_with_git_suffix(self):
        """Test parsing HTTPS URL with .git suffix."""
        owner, name = parse_github_url("https://github.com/owner/repo.git")
        assert owner == "owner"
        assert name == "repo"
    
    def test_parse_ssh_url(self):
        """Test parsing SSH URL."""
        owner, name = parse_github_url("git@github.com:owner/repo")
        assert owner == "owner"
        assert name == "repo"
    
    def test_parse_ssh_url_with_git_suffix(self):
        """Test parsing SSH URL with .git suffix."""
        owner, name = parse_github_url("git@github.com:owner/repo.git")
        assert owner == "owner"
        assert name == "repo"
    
    def test_parse_url_with_trailing_slash(self):
        """Test parsing URL with trailing slash."""
        owner, name = parse_github_url("https://github.com/owner/repo/")
        assert owner == "owner"
        assert name == "repo"
    
    def test_parse_invalid_url_raises_error(self):
        """Test that invalid URL raises ValueError."""
        with pytest.raises(ValueError):
            parse_github_url("https://github.com/")
    
    def test_parse_url_with_subdirectory(self):
        """Test parsing URL with subdirectory (takes first two parts)."""
        owner, name = parse_github_url("https://github.com/owner/repo/tree/main")
        assert owner == "owner"
        assert name == "repo"


class TestRepoInfo:
    """Tests for RepoInfo dataclass."""
    
    def test_create_repo_info(self):
        """Test creating RepoInfo."""
        repo = RepoInfo(
            name="test-repo",
            owner="testuser",
            full_name="testuser/test-repo",
            url="https://github.com/testuser/test-repo.git",
            default_branch="main",
            description="A test repository",
            is_private=False,
        )
        
        assert repo.name == "test-repo"
        assert repo.owner == "testuser"
        assert repo.full_name == "testuser/test-repo"
        assert repo.default_branch == "main"
        assert repo.is_private is False


class TestFileChange:
    """Tests for FileChange dataclass."""
    
    def test_create_file_change(self):
        """Test creating FileChange."""
        change = FileChange(
            path="src/main.py",
            status="modified",
            additions=10,
            deletions=5,
        )
        
        assert change.path == "src/main.py"
        assert change.status == "modified"
        assert change.additions == 10
        assert change.deletions == 5
        assert change.diff is None
    
    def test_create_file_change_with_diff(self):
        """Test creating FileChange with diff."""
        change = FileChange(
            path="src/main.py",
            status="added",
            diff="+print('hello')",
        )
        
        assert change.diff == "+print('hello')"


class TestBranchInfo:
    """Tests for BranchInfo dataclass."""
    
    def test_create_branch_info(self):
        """Test creating BranchInfo."""
        branch = BranchInfo(
            name="feature/test",
            is_current=True,
            commit_sha="abc12345",
        )
        
        assert branch.name == "feature/test"
        assert branch.is_current is True
        assert branch.commit_sha == "abc12345"
    
    def test_branch_info_defaults(self):
        """Test BranchInfo default values."""
        branch = BranchInfo(name="main")
        
        assert branch.is_current is False
        assert branch.commit_sha is None


class TestGitHubService:
    """Tests for GitHubService class."""
    
    def test_init_with_token(self):
        """Test initialization with token."""
        service = GitHubService(token="test-token")
        assert service.token == "test-token"
    
    def test_build_authenticated_url(self):
        """Test building authenticated URL."""
        service = GitHubService(token="test-token")
        
        url = service._build_authenticated_url("https://github.com/owner/repo.git")
        
        assert "test-token@github.com" in url
    
    def test_build_authenticated_url_no_token(self):
        """Test building URL without token returns original."""
        # Patch settings to ensure no default token
        with patch('app.service.github_service.settings') as mock_settings:
            mock_settings.github_token = None
            service = GitHubService(token=None)
            
            original_url = "https://github.com/owner/repo.git"
            url = service._build_authenticated_url(original_url)
            
            assert url == original_url
    
    def test_build_authenticated_url_non_github(self):
        """Test building URL for non-GitHub returns original."""
        service = GitHubService(token="test-token")
        
        original_url = "https://gitlab.com/owner/repo.git"
        url = service._build_authenticated_url(original_url)
        
        assert url == original_url
    
    def test_build_authenticated_url_with_existing_token(self):
        """Test building URL when URL already has token."""
        service = GitHubService(token="new-token")
        
        url = service._build_authenticated_url(
            "https://old-token@github.com/owner/repo.git"
        )
        
        assert "new-token@github.com" in url
        assert "old-token" not in url
    
    @pytest.mark.asyncio
    async def test_get_local_changes_empty_repo(self, mock_git_repo, temp_workspace):
        """Test getting changes from clean repo."""
        service = GitHubService()
        
        changes = await service.get_local_changes(str(temp_workspace))
        
        assert isinstance(changes, list)
        # Clean repo should have no changes
        assert len(changes) == 0
    
    @pytest.mark.asyncio
    async def test_get_local_changes_with_new_file(self, mock_git_repo, temp_workspace):
        """Test getting changes with new file."""
        # Create new file
        new_file = temp_workspace / "new_file.py"
        new_file.write_text("print('hello')")
        
        service = GitHubService()
        changes = await service.get_local_changes(str(temp_workspace))
        
        assert len(changes) == 1
        assert changes[0].path == "new_file.py"
        assert changes[0].status == "added"
    
    @pytest.mark.asyncio
    async def test_get_local_changes_with_diff(self, mock_git_repo, temp_workspace):
        """Test getting changes with diff content."""
        # Create new file
        new_file = temp_workspace / "new_file.py"
        new_file.write_text("print('hello')")
        
        service = GitHubService()
        changes = await service.get_local_changes(str(temp_workspace), include_diff=True)
        
        assert len(changes) == 1
        assert changes[0].diff is not None
        assert "+print('hello')" in changes[0].diff
    
    @pytest.mark.asyncio
    async def test_get_file_diff_untracked(self, mock_git_repo, temp_workspace):
        """Test getting diff for untracked file."""
        # Create new file
        new_file = temp_workspace / "new_file.py"
        new_file.write_text("print('hello')\nprint('world')")
        
        service = GitHubService()
        diff = await service.get_file_diff(str(temp_workspace), "new_file.py")
        
        assert "+print('hello')" in diff
        assert "+print('world')" in diff
    
    @pytest.mark.asyncio
    async def test_commit_changes(self, mock_git_repo, temp_workspace):
        """Test committing changes."""
        # Create new file
        new_file = temp_workspace / "new_file.py"
        new_file.write_text("print('hello')")
        
        service = GitHubService()
        sha = await service.commit_changes(
            str(temp_workspace),
            "Add new file",
        )
        
        assert sha is not None
        assert len(sha) == 40  # SHA length
    
    @pytest.mark.asyncio
    async def test_create_branch(self, mock_git_repo, temp_workspace):
        """Test creating a branch."""
        service = GitHubService()
        
        result = await service.create_branch(
            str(temp_workspace),
            "feature/test",
            checkout=True,
        )
        
        assert result is True
        
        # Verify branch was created and checked out
        current = await service.get_current_branch(str(temp_workspace))
        assert current == "feature/test"
    
    @pytest.mark.asyncio
    async def test_list_branches(self, mock_git_repo, temp_workspace):
        """Test listing branches."""
        service = GitHubService()
        
        # Create additional branch
        await service.create_branch(str(temp_workspace), "feature/test", checkout=False)
        
        branches = await service.list_branches(str(temp_workspace))
        
        assert len(branches) >= 2
        branch_names = [b.name for b in branches]
        assert "feature/test" in branch_names
    
    @pytest.mark.asyncio
    async def test_checkout_branch(self, mock_git_repo, temp_workspace):
        """Test checking out a branch."""
        service = GitHubService()
        
        # Create branch without checkout
        await service.create_branch(str(temp_workspace), "feature/test", checkout=False)
        
        # Checkout the branch
        result = await service.checkout_branch(str(temp_workspace), "feature/test")
        
        assert result is True
        
        current = await service.get_current_branch(str(temp_workspace))
        assert current == "feature/test"
    
    @pytest.mark.asyncio
    async def test_get_current_branch(self, mock_git_repo, temp_workspace):
        """Test getting current branch."""
        service = GitHubService()
        
        branch = await service.get_current_branch(str(temp_workspace))
        
        assert branch in ["main", "master"]  # Default branch


class TestGitOperationError:
    """Tests for GitOperationError exception."""
    
    def test_create_error(self):
        """Test creating GitOperationError."""
        error = GitOperationError(
            message="Clone failed",
            operation="clone",
            details={"exit_code": 128},
        )
        
        assert str(error) == "Clone failed"
        assert error.operation == "clone"
        assert error.details["exit_code"] == 128


class TestGitHubAPIError:
    """Tests for GitHubAPIError exception."""
    
    def test_create_error(self):
        """Test creating GitHubAPIError."""
        error = GitHubAPIError(
            message="Rate limit exceeded",
            status_code=403,
            details={"retry_after": 60},
        )
        
        assert str(error) == "Rate limit exceeded"
        assert error.status_code == 403
        assert error.details["retry_after"] == 60

