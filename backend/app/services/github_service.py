"""GitHub API integration service."""

import os
import asyncio
from typing import Optional
from pathlib import Path
from dataclasses import dataclass
from urllib.parse import urlparse

from github import Github, GithubException
from git import Repo, GitCommandError

from ..config import get_settings

settings = get_settings()


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


@dataclass
class PullRequestInfo:
    """Pull request information."""
    number: int
    title: str
    url: str
    state: str
    head_branch: str
    base_branch: str


def parse_github_url(url: str) -> tuple[str, str]:
    """Parse GitHub URL to extract owner and repo name.
    
    Args:
        url: GitHub repository URL
        
    Returns:
        Tuple of (owner, repo_name)
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


class GitHubService:
    """Service for GitHub operations."""
    
    def __init__(self, token: Optional[str] = None):
        """Initialize GitHub service.
        
        Args:
            token: GitHub personal access token (uses config if not provided)
        """
        self.token = token or settings.github_token
        self._client: Optional[Github] = None
    
    @property
    def client(self) -> Github:
        """Get GitHub client."""
        if self._client is None:
            self._client = Github(self.token)
        return self._client
    
    async def get_repo_info(self, repo_url: str) -> RepoInfo:
        """Get repository information.
        
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
            repos = [r for r in repos if query_lower in r.name.lower() or (r.description and query_lower in r.description.lower())]
        
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
        if self.token and "github.com" in repo_url:
            if repo_url.startswith("https://"):
                repo_url = repo_url.replace(
                    "https://github.com",
                    f"https://{self.token}@github.com"
                )
        
        # Ensure target directory is empty or doesn't exist
        target = Path(target_path)
        if target.exists():
            import shutil
            shutil.rmtree(target)
        
        target.mkdir(parents=True, exist_ok=True)
        
        # Clone repository
        clone_kwargs = {"depth": 1}  # Shallow clone for speed
        if branch:
            clone_kwargs["branch"] = branch
        
        repo = await asyncio.to_thread(
            Repo.clone_from,
            repo_url,
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
        clone_url = repo_url
        if self.token and "github.com" in repo_url:
            if repo_url.startswith("https://"):
                clone_url = repo_url.replace(
                    "https://github.com",
                    f"https://{self.token}@github.com"
                )
        
        # Build git clone command
        # Only specify branch if explicitly provided and not empty
        branch_arg = f"-b {branch}" if branch and branch.strip() else ""
        git_command = f"git clone --depth 1 {branch_arg} {clone_url} /workspace".strip()
        
        # Execute in container
        exit_code, output = await docker_service.execute_command(
            session_id=session_id,
            command=git_command,
            workdir="/workspace"
        )
        
        if exit_code != 0:
            raise RuntimeError(f"Failed to clone repository: {output}")
    
    async def get_local_changes(self, repo_path: str) -> list[FileChange]:
        """Get list of local changes in repository.
        
        Args:
            repo_path: Path to local repository
            
        Returns:
            List of FileChange objects
        """
        repo = Repo(repo_path)
        changes = []
        
        # Get staged changes
        for diff in repo.index.diff("HEAD"):
            changes.append(FileChange(
                path=diff.a_path or diff.b_path,
                status="modified" if diff.change_type == "M" else diff.change_type.lower(),
            ))
        
        # Get unstaged changes
        for diff in repo.index.diff(None):
            changes.append(FileChange(
                path=diff.a_path or diff.b_path,
                status="modified" if diff.change_type == "M" else diff.change_type.lower(),
            ))
        
        # Get untracked files
        for path in repo.untracked_files:
            changes.append(FileChange(
                path=path,
                status="added",
            ))
        
        return changes
    
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
            # Update remote URL with token
            remote_obj = repo.remote(remote)
            old_url = remote_obj.url
            if "github.com" in old_url and "@" not in old_url:
                new_url = old_url.replace(
                    "https://github.com",
                    f"https://{self.token}@github.com"
                )
                remote_obj.set_url(new_url)
        
        await asyncio.to_thread(
            repo.remote(remote).push,
            branch,
        )
        
        return True
    
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
    
    async def list_branches(self, repo_path: str) -> list[str]:
        """List branches in local repository.
        
        Args:
            repo_path: Path to local repository
            
        Returns:
            List of branch names
        """
        repo = Repo(repo_path)
        return [head.name for head in repo.heads]
    
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
        
        await asyncio.to_thread(
            repo.remote(remote).pull,
            branch,
        )
        
        return True
    
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


# Global GitHub service instance
github_service = GitHubService()

