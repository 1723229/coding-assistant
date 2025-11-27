"""GitHub API integration service with tool abstraction."""

import os
import asyncio
from typing import Optional, TypeVar, Callable, Any
from pathlib import Path
from dataclasses import dataclass
from urllib.parse import urlparse
from functools import wraps
from enum import Enum

from github import Github, GithubException
from git import Repo, GitCommandError

from app.config import get_settings, GitHubConfig

settings = get_settings()

T = TypeVar('T')


class GitOperationError(Exception):
    """Custom exception for Git operations."""
    
    def __init__(self, message: str, operation: str, details: Optional[dict] = None):
        super().__init__(message)
        self.operation = operation
        self.details = details or {}


class GitHubAPIError(Exception):
    """Custom exception for GitHub API operations."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


@dataclass
class RepoInfo:
    """Repository information."""
    name: str
    owner: str
    full_name: str
    url: str
    default_branch: str
    description: Optional[str]
    is_private: bool


@dataclass
class FileChange:
    """File change information."""
    path: str
    status: str  # added, modified, deleted, renamed
    additions: int = 0
    deletions: int = 0
    diff: Optional[str] = None


@dataclass
class PullRequestInfo:
    """Pull request information."""
    number: int
    title: str
    url: str
    state: str
    head_branch: str
    base_branch: str


@dataclass 
class BranchInfo:
    """Branch information."""
    name: str
    is_current: bool = False
    commit_sha: Optional[str] = None


def parse_github_url(url: str) -> tuple[str, str]:
    """Parse GitHub URL to extract owner and repo name.
    
    Args:
        url: GitHub repository URL
        
    Returns:
        Tuple of (owner, repo_name)
        
    Raises:
        ValueError: If URL format is invalid
    """
    # Handle various URL formats
    url = url.rstrip("/").rstrip(".git")
    
    if url.startswith("git@github.com:"):
        # SSH format: git@github.com:owner/repo
        path = url.replace("git@github.com:", "")
    else:
        # HTTPS format: https://github.com/owner/repo
        parsed = urlparse(url)
        path = parsed.path.lstrip("/")
    
    parts = path.split("/")
    if len(parts) >= 2:
        return parts[0], parts[1]
    
    raise ValueError(f"Invalid GitHub URL: {url}")


def git_operation(operation_name: str):
    """Decorator for Git operations with error handling."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except GitCommandError as e:
                raise GitOperationError(
                    message=f"Git {operation_name} failed: {str(e)}",
                    operation=operation_name,
                    details={"stderr": e.stderr if hasattr(e, 'stderr') else None}
                )
            except Exception as e:
                if isinstance(e, (GitOperationError, GitHubAPIError)):
                    raise
                raise GitOperationError(
                    message=f"Git {operation_name} failed: {str(e)}",
                    operation=operation_name,
                )
        return wrapper
    return decorator


def github_api_operation(operation_name: str):
    """Decorator for GitHub API operations with error handling."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except GithubException as e:
                raise GitHubAPIError(
                    message=f"GitHub API {operation_name} failed: {str(e)}",
                    status_code=e.status if hasattr(e, 'status') else None,
                    details={"data": e.data if hasattr(e, 'data') else None}
                )
            except Exception as e:
                if isinstance(e, (GitOperationError, GitHubAPIError)):
                    raise
                raise GitHubAPIError(
                    message=f"GitHub API {operation_name} failed: {str(e)}",
                )
        return wrapper
    return decorator


class GitHubService:
    """Service for GitHub operations with tool abstraction."""
    
    def __init__(self, token: Optional[str] = None):
        """Initialize GitHub service.
        
        Args:
            token: GitHub personal access token (uses config if not provided)
        """
        self.token = token or settings.github_token
        self._client: Optional[Github] = None
    
    @property
    def client(self) -> Github:
        """Get GitHub client (lazy initialization)."""
        if self._client is None:
            if not self.token:
                raise GitHubAPIError(
                    "GitHub token not configured",
                    details={"hint": "Please configure a GitHub token in settings"}
                )
            self._client = Github(self.token)
        return self._client
    
    def _build_authenticated_url(self, url: str) -> str:
        """Build URL with embedded token for authentication.
        
        Args:
            url: Original GitHub URL
            
        Returns:
            URL with embedded token
        """
        if not self.token or "github.com" not in url:
            return url
            
        if not url.startswith("https://"):
            return url
            
        # Remove any existing credentials from URL
        if "@github.com" in url:
            path_start = url.find("@github.com") + len("@github.com")
            path = url[path_start:]
        else:
            path_start = url.find("github.com") + len("github.com")
            path = url[path_start:]
        
        return f"https://{self.token}@github.com{path}"
    
    # ===================
    # GitHub API Operations
    # ===================
    
    @github_api_operation("get_repo_info")
    async def get_repo_info(self, repo_url: str) -> RepoInfo:
        """Get repository information from GitHub API.
        
        Args:
            repo_url: GitHub repository URL
            
        Returns:
            RepoInfo with repository details
        """
        owner, name = parse_github_url(repo_url)
        
        repo = await asyncio.to_thread(
            self.client.get_repo,
            f"{owner}/{name}",
        )
        
        return RepoInfo(
            name=repo.name,
            owner=repo.owner.login,
            full_name=repo.full_name,
            url=repo.clone_url,
            default_branch=repo.default_branch,
            description=repo.description,
            is_private=repo.private,
        )
    
    @github_api_operation("list_user_repos")
    async def list_user_repos(
        self,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 30,
    ) -> list[RepoInfo]:
        """List authenticated user's repositories.
        
        Args:
            query: Optional search query to filter repos
            page: Page number (1-indexed)
            per_page: Results per page
            
        Returns:
            List of RepoInfo objects
        """
        user = await asyncio.to_thread(self.client.get_user)
        repos = await asyncio.to_thread(
            lambda: list(user.get_repos(sort="updated", direction="desc"))
        )
        
        # Filter by query if provided
        if query:
            query_lower = query.lower()
            repos = [
                r for r in repos 
                if query_lower in r.name.lower() or 
                   (r.description and query_lower in r.description.lower())
            ]
        
        # Pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        repos = repos[start_idx:end_idx]
        
        return [
            RepoInfo(
                name=r.name,
                owner=r.owner.login,
                full_name=r.full_name,
                url=r.clone_url,
                default_branch=r.default_branch,
                description=r.description,
                is_private=r.private,
            )
            for r in repos
        ]
    
    @github_api_operation("create_pull_request")
    async def create_pull_request(
        self,
        repo_url: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: Optional[str] = None,
    ) -> PullRequestInfo:
        """Create a pull request on GitHub.
        
        Args:
            repo_url: GitHub repository URL
            title: PR title
            body: PR description
            head_branch: Source branch
            base_branch: Target branch (default: repo's default branch)
            
        Returns:
            PullRequestInfo with PR details
        """
        owner, name = parse_github_url(repo_url)
        
        gh_repo = await asyncio.to_thread(
            self.client.get_repo,
            f"{owner}/{name}",
        )
        
        if base_branch is None:
            base_branch = gh_repo.default_branch
        
        pr = await asyncio.to_thread(
            gh_repo.create_pull,
            title=title,
            body=body,
            head=head_branch,
            base=base_branch,
        )
        
        return PullRequestInfo(
            number=pr.number,
            title=pr.title,
            url=pr.html_url,
            state=pr.state,
            head_branch=head_branch,
            base_branch=base_branch,
        )
    
    @github_api_operation("get_file_content")
    async def get_file_content(
        self,
        repo_url: str,
        file_path: str,
        ref: Optional[str] = None,
    ) -> str:
        """Get file content from GitHub.
        
        Args:
            repo_url: GitHub repository URL
            file_path: Path to file in repository
            ref: Git reference (branch, tag, commit)
            
        Returns:
            File content as string
        """
        owner, name = parse_github_url(repo_url)
        
        gh_repo = await asyncio.to_thread(
            self.client.get_repo,
            f"{owner}/{name}",
        )
        
        kwargs = {}
        if ref:
            kwargs["ref"] = ref
        
        content = await asyncio.to_thread(
            gh_repo.get_contents,
            file_path,
            **kwargs,
        )
        
        return content.decoded_content.decode("utf-8")
    
    @github_api_operation("list_repo_contents")
    async def list_repo_contents(
        self,
        repo_url: str,
        path: str = "",
        ref: Optional[str] = None,
    ) -> list[dict]:
        """List contents of a directory in repository.
        
        Args:
            repo_url: GitHub repository URL
            path: Path to directory
            ref: Git reference
            
        Returns:
            List of file/directory info dicts
        """
        owner, name = parse_github_url(repo_url)
        
        gh_repo = await asyncio.to_thread(
            self.client.get_repo,
            f"{owner}/{name}",
        )
        
        kwargs = {}
        if ref:
            kwargs["ref"] = ref
        
        contents = await asyncio.to_thread(
            gh_repo.get_contents,
            path,
            **kwargs,
        )
        
        if not isinstance(contents, list):
            contents = [contents]
        
        return [
            {
                "name": c.name,
                "path": c.path,
                "type": c.type,
                "size": c.size,
                "sha": c.sha,
            }
            for c in contents
        ]
    
    # ===================
    # Local Git Operations
    # ===================
    
    @git_operation("clone")
    async def clone_repo(
        self,
        repo_url: str,
        target_path: str,
        branch: Optional[str] = None,
    ) -> Repo:
        """Clone a repository.
        
        Args:
            repo_url: GitHub repository URL
            target_path: Local path to clone to
            branch: Branch to checkout (default: repo's default branch)
            
        Returns:
            GitPython Repo object
        """
        # Add token to URL for private repos
        clone_url = self._build_authenticated_url(repo_url)
        
        # Ensure target directory is empty or doesn't exist
        target = Path(target_path)
        if target.exists():
            import shutil
            shutil.rmtree(target)
        
        target.mkdir(parents=True, exist_ok=True)
        
        # Configure Git for HTTP/1.1 to avoid HTTP/2 framing issues
        import subprocess
        await asyncio.to_thread(
            subprocess.run,
            ["git", "config", "--global", "http.version", "HTTP/1.1"],
            check=False,  # Don't fail if already set
        )

        # Clone repository
        clone_kwargs = {}
        if branch:
            clone_kwargs["branch"] = branch

        repo = await asyncio.to_thread(
            Repo.clone_from,
            clone_url,
            target_path,
            **clone_kwargs,
        )
        
        return repo
    
    async def clone_repo_in_container(
        self,
        session_id: str,
        repo_url: str,
        branch: Optional[str] = None,
    ) -> None:
        """Clone a repository inside a Docker container.
        
        Args:
            session_id: Session identifier for the container
            repo_url: GitHub repository URL
            branch: Branch to checkout (default: main)
        """
        from .docker_service import docker_service
        
        # Add token to URL for private repos
        clone_url = self._build_authenticated_url(repo_url)
        
        # Build git clone command
        branch_arg = f"-b {branch}" if branch and branch.strip() else ""
        git_command = f"git clone {branch_arg} {clone_url} /workspace".strip()
        
        # Execute in container
        exit_code, output = await docker_service.execute_command(
            session_id=session_id,
            command=git_command,
            workdir="/workspace"
        )
        
        if exit_code != 0:
            raise GitOperationError(
                message=f"Failed to clone repository: {output}",
                operation="clone_in_container",
                details={"exit_code": exit_code, "output": output}
            )
    
    @git_operation("get_local_changes")
    async def get_local_changes(
        self, 
        repo_path: str, 
        include_diff: bool = False
    ) -> list[FileChange]:
        """Get list of local changes in repository.
        
        Args:
            repo_path: Path to local repository
            include_diff: Whether to include diff content
            
        Returns:
            List of FileChange objects
        """
        repo = Repo(repo_path)
        changes = []
        seen_paths = set()
        
        # Get staged changes
        for diff in repo.index.diff("HEAD"):
            path = diff.a_path or diff.b_path
            if path in seen_paths:
                continue
            seen_paths.add(path)
            
            diff_content = None
            if include_diff:
                try:
                    diff_content = repo.git.diff("HEAD", "--", path)
                except:
                    pass
            
            changes.append(FileChange(
                path=path,
                status="modified" if diff.change_type == "M" else diff.change_type.lower(),
                diff=diff_content,
            ))
        
        # Get unstaged changes
        for diff in repo.index.diff(None):
            path = diff.a_path or diff.b_path
            if path in seen_paths:
                continue
            seen_paths.add(path)
            
            diff_content = None
            if include_diff:
                try:
                    diff_content = repo.git.diff("--", path)
                except:
                    pass
            
            changes.append(FileChange(
                path=path,
                status="modified" if diff.change_type == "M" else diff.change_type.lower(),
                diff=diff_content,
            ))
        
        # Get untracked files
        for path in repo.untracked_files:
            if path in seen_paths:
                continue
            seen_paths.add(path)
            
            diff_content = None
            if include_diff:
                try:
                    file_path = Path(repo_path) / path
                    if file_path.exists():
                        content = file_path.read_text(errors='replace')
                        lines = content.split('\n')
                        diff_lines = [f"+{line}" for line in lines]
                        diff_content = f"--- /dev/null\n+++ b/{path}\n@@ -0,0 +1,{len(lines)} @@\n" + '\n'.join(diff_lines)
                except:
                    pass
            
            changes.append(FileChange(
                path=path,
                status="added",
                diff=diff_content,
            ))
        
        return changes
    
    @git_operation("get_file_diff")
    async def get_file_diff(self, repo_path: str, file_path: str) -> str:
        """Get diff for a specific file.
        
        Args:
            repo_path: Path to local repository
            file_path: Path to the file relative to repo root
            
        Returns:
            Unified diff string
        """
        repo = Repo(repo_path)
        
        # Check if file is untracked
        if file_path in repo.untracked_files:
            full_path = Path(repo_path) / file_path
            if full_path.exists():
                content = full_path.read_text(errors='replace')
                lines = content.split('\n')
                diff_lines = [f"+{line}" for line in lines]
                return f"--- /dev/null\n+++ b/{file_path}\n@@ -0,0 +1,{len(lines)} @@\n" + '\n'.join(diff_lines)
            return ""
        
        # Try to get diff from staged changes first
        try:
            diff = repo.git.diff("HEAD", "--", file_path)
            if diff:
                return diff
        except:
            pass
        
        # Try to get diff from unstaged changes
        try:
            diff = repo.git.diff("--", file_path)
            if diff:
                return diff
        except:
            pass
        
        return ""
    
    @git_operation("commit")
    async def commit_changes(
        self,
        repo_path: str,
        message: str,
        files: Optional[list[str]] = None,
    ) -> str:
        """Commit changes to repository.
        
        Args:
            repo_path: Path to local repository
            message: Commit message
            files: Specific files to commit (None for all changes)
            
        Returns:
            Commit SHA
        """
        repo = Repo(repo_path)
        
        if files:
            repo.index.add(files)
        else:
            # Add all changes
            repo.git.add(A=True)
        
        commit = repo.index.commit(message)
        return commit.hexsha
    
    @git_operation("push")
    async def push_changes(
        self,
        repo_path: str,
        remote: str = "origin",
        branch: Optional[str] = None,
    ) -> bool:
        """Push committed changes to remote.
        
        Args:
            repo_path: Path to local repository
            remote: Remote name
            branch: Branch to push (default: current branch)
            
        Returns:
            True if successful
        """
        repo = Repo(repo_path)
        
        if branch is None:
            branch = repo.active_branch.name
        
        # Set up credentials
        if self.token:
            remote_obj = repo.remote(remote)
            old_url = remote_obj.url
            new_url = self._build_authenticated_url(old_url)
            if new_url != old_url:
                remote_obj.set_url(new_url)
        
        await asyncio.to_thread(
            repo.remote(remote).push,
            branch,
        )
        
        return True
    
    @git_operation("pull")
    async def pull_changes(
        self,
        repo_path: str,
        remote: str = "origin",
        branch: Optional[str] = None,
    ) -> bool:
        """Pull changes from remote.
        
        Args:
            repo_path: Path to local repository
            remote: Remote name
            branch: Branch to pull (default: current branch)
            
        Returns:
            True if successful
        """
        repo = Repo(repo_path)
        
        if branch is None:
            branch = repo.active_branch.name
        
        # Set up credentials if token is available
        if self.token:
            remote_obj = repo.remote(remote)
            old_url = remote_obj.url
            new_url = self._build_authenticated_url(old_url)
            if new_url != old_url:
                remote_obj.set_url(new_url)
        
        await asyncio.to_thread(
            repo.remote(remote).pull,
            branch,
        )
        
        return True
    
    @git_operation("create_branch")
    async def create_branch(
        self,
        repo_path: str,
        branch_name: str,
        checkout: bool = True,
    ) -> bool:
        """Create a new branch.
        
        Args:
            repo_path: Path to local repository
            branch_name: Name for new branch
            checkout: Whether to checkout the new branch
            
        Returns:
            True if successful
        """
        repo = Repo(repo_path)
        
        # Create branch
        new_branch = repo.create_head(branch_name)
        
        if checkout:
            new_branch.checkout()
        
        return True
    
    @git_operation("list_branches")
    async def list_branches(self, repo_path: str) -> list[BranchInfo]:
        """List branches in local repository.
        
        Args:
            repo_path: Path to local repository
            
        Returns:
            List of BranchInfo objects
        """
        repo = Repo(repo_path)
        current_branch = repo.active_branch.name
        
        return [
            BranchInfo(
                name=head.name,
                is_current=(head.name == current_branch),
                commit_sha=head.commit.hexsha[:8],
            )
            for head in repo.heads
        ]
    
    @git_operation("checkout")
    async def checkout_branch(self, repo_path: str, branch_name: str) -> bool:
        """Checkout a branch.
        
        Args:
            repo_path: Path to local repository
            branch_name: Branch to checkout
            
        Returns:
            True if successful
        """
        repo = Repo(repo_path)
        repo.git.checkout(branch_name)
        return True
    
    @git_operation("get_current_branch")
    async def get_current_branch(self, repo_path: str) -> str:
        """Get the current branch name.
        
        Args:
            repo_path: Path to local repository
            
        Returns:
            Current branch name
        """
        repo = Repo(repo_path)
        return repo.active_branch.name
    
    @git_operation("get_remote_url")
    async def get_remote_url(self, repo_path: str, remote: str = "origin") -> str:
        """Get the remote URL for a repository.
        
        Args:
            repo_path: Path to local repository
            remote: Remote name
            
        Returns:
            Remote URL
        """
        repo = Repo(repo_path)
        return repo.remote(remote).url


# Global GitHub service instance (for backward compatibility)
github_service = GitHubService()
