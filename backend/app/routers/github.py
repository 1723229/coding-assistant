"""
GitHub integration REST API.

Provides endpoints for GitHub repository operations.
"""

import uuid
from typing import Optional, List
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_db
from app.db.schemas import (
    GitHubTokenCreate,
    GitHubTokenResponse,
    CloneRepoRequest,
    CommitRequest,
    PushRequest,
    CreateBranchRequest,
    CreatePRRequest,
    RepoInfoResponse,
    FileChangeResponse,
    PRResponse,
)
from app.db.repository import SessionRepository, GitHubTokenRepository
from app.services.github_service import GitHubService, github_service

router = APIRouter()

# Repository instances
session_repo = SessionRepository()
token_repo = GitHubTokenRepository()


def mask_token(token: str) -> str:
    """Mask token for display (show first 4 and last 4 characters)."""
    if len(token) <= 8:
        return "****"
    return f"{token[:4]}{'*' * (len(token) - 8)}{token[-4:]}"


# ===================
# Repository Operations
# ===================

@router.get("/repo/info", response_model=RepoInfoResponse)
async def get_repo_info(
    url: str = Query(..., description="GitHub repository URL"),
) -> RepoInfoResponse:
    """Get repository information from GitHub."""
    try:
        info = await github_service.get_repo_info(url)
        return RepoInfoResponse(
            name=info.name,
            owner=info.owner,
            full_name=info.full_name,
            url=info.url,
            default_branch=info.default_branch,
            description=info.description,
            is_private=info.is_private,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/clone")
async def clone_repository(
    session_id: str,
    data: CloneRepoRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """Clone a GitHub repository to session workspace."""
    session = await session_repo.get_session_by_id(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.workspace_path:
        raise HTTPException(status_code=400, detail="Session has no workspace")
    
    # Get the active GitHub token
    token_record = await token_repo.get_latest_token(platform="GitHub")
    
    # Create a service instance with the user's token
    service = GitHubService(token=token_record.token if token_record else None)
    
    try:
        await service.clone_repo(
            repo_url=data.repo_url,
            target_path=session.workspace_path,
            branch=data.branch,
        )
        
        # Update session with GitHub info
        await session_repo.update_session(
            session_id,
            github_repo_url=data.repo_url,
            github_branch=data.branch or "main",
        )
        
        return {
            "status": "cloned",
            "repo_url": data.repo_url,
            "workspace_path": session.workspace_path,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/changes", response_model=List[FileChangeResponse])
async def get_changes(
    session_id: str,
    include_diff: bool = Query(default=False, description="Include diff content"),
    db: AsyncSession = Depends(get_async_db),
) -> List[FileChangeResponse]:
    """Get local changes in repository."""
    session = await session_repo.get_session_by_id(session_id)
    
    if not session or not session.workspace_path:
        raise HTTPException(status_code=404, detail="Session or workspace not found")
    
    try:
        changes = await github_service.get_local_changes(session.workspace_path, include_diff=include_diff)
        return [
            FileChangeResponse(path=c.path, status=c.status, diff=c.diff)
            for c in changes
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/diff/{file_path:path}")
async def get_file_diff(
    session_id: str,
    file_path: str,
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """Get diff for a specific file."""
    session = await session_repo.get_session_by_id(session_id)
    
    if not session or not session.workspace_path:
        raise HTTPException(status_code=404, detail="Session or workspace not found")
    
    try:
        diff = await github_service.get_file_diff(session.workspace_path, file_path)
        return {"path": file_path, "diff": diff}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/commit")
async def commit_changes(
    session_id: str,
    data: CommitRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """Commit changes to local repository."""
    session = await session_repo.get_session_by_id(session_id)
    
    if not session or not session.workspace_path:
        raise HTTPException(status_code=404, detail="Session or workspace not found")
    
    try:
        sha = await github_service.commit_changes(
            repo_path=session.workspace_path,
            message=data.message,
            files=data.files,
        )
        return {"status": "committed", "sha": sha}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/push")
async def push_changes(
    session_id: str,
    data: PushRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """Push committed changes to GitHub."""
    session = await session_repo.get_session_by_id(session_id)
    
    if not session or not session.workspace_path:
        raise HTTPException(status_code=404, detail="Session or workspace not found")
    
    # Get the active GitHub token
    token_record = await token_repo.get_latest_token(platform="GitHub")
    
    # Create a service instance with the user's token
    service = GitHubService(token=token_record.token if token_record else None)
    
    try:
        await service.push_changes(
            repo_path=session.workspace_path,
            remote=data.remote,
            branch=data.branch,
        )
        return {"status": "pushed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/branch")
async def create_branch(
    session_id: str,
    data: CreateBranchRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """Create a new branch."""
    session = await session_repo.get_session_by_id(session_id)
    
    if not session or not session.workspace_path:
        raise HTTPException(status_code=404, detail="Session or workspace not found")
    
    try:
        await github_service.create_branch(
            repo_path=session.workspace_path,
            branch_name=data.branch_name,
            checkout=data.checkout,
        )
        
        if data.checkout:
            await session_repo.update_session(session_id, github_branch=data.branch_name)
        
        return {"status": "created", "branch": data.branch_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/branches")
async def list_branches(
    session_id: str,
    db: AsyncSession = Depends(get_async_db),
) -> List[str]:
    """List branches in repository."""
    session = await session_repo.get_session_by_id(session_id)
    
    if not session or not session.workspace_path:
        raise HTTPException(status_code=404, detail="Session or workspace not found")
    
    try:
        branches = await github_service.list_branches(session.workspace_path)
        return [b.name for b in branches]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/checkout")
async def checkout_branch(
    session_id: str,
    branch: str = Query(..., description="Branch to checkout"),
    db: AsyncSession = Depends(get_async_db),
):
    """Checkout a branch."""
    session = await session_repo.get_session_by_id(session_id)
    
    if not session or not session.workspace_path:
        raise HTTPException(status_code=404, detail="Session or workspace not found")
    
    try:
        await github_service.checkout_branch(session.workspace_path, branch)
        await session_repo.update_session(session_id, github_branch=branch)
        return {"status": "checked out", "branch": branch}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/pull")
async def pull_changes(
    session_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """Pull changes from remote."""
    session = await session_repo.get_session_by_id(session_id)

    if not session or not session.workspace_path:
        raise HTTPException(status_code=404, detail="Session or workspace not found")

    # Check if workspace is a valid git repository
    workspace = Path(session.workspace_path)
    git_dir = workspace / ".git"
    if not git_dir.exists():
        raise HTTPException(
            status_code=400,
            detail="No git repository found. Please clone a repository first."
        )

    # Get the active GitHub token
    token_record = await token_repo.get_latest_token(platform="GitHub")

    # Create a service instance with the user's token
    service = GitHubService(token=token_record.token if token_record else None)

    try:
        await service.pull_changes(session.workspace_path)
        return {"status": "pulled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/pr", response_model=PRResponse)
async def create_pull_request(
    session_id: str,
    data: CreatePRRequest,
    db: AsyncSession = Depends(get_async_db),
) -> PRResponse:
    """Create a pull request on GitHub."""
    session = await session_repo.get_session_by_id(session_id)
    
    if not session or not session.github_repo_url:
        raise HTTPException(status_code=404, detail="Session not found or no GitHub repo bound")
    
    try:
        pr = await github_service.create_pull_request(
            repo_url=session.github_repo_url,
            title=data.title,
            body=data.body,
            head_branch=data.head_branch,
            base_branch=data.base_branch,
        )
        return PRResponse(
            number=pr.number,
            title=pr.title,
            url=pr.url,
            state=pr.state,
            head_branch=pr.head_branch,
            base_branch=pr.base_branch,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repo/contents")
async def get_repo_contents(
    url: str = Query(..., description="GitHub repository URL"),
    path: str = Query(default="", description="Path within repository"),
    ref: Optional[str] = Query(default=None, description="Git reference"),
):
    """List contents of a directory in GitHub repository."""
    try:
        contents = await github_service.list_repo_contents(url, path, ref)
        return contents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repo/file")
async def get_repo_file(
    url: str = Query(..., description="GitHub repository URL"),
    path: str = Query(..., description="File path"),
    ref: Optional[str] = Query(default=None, description="Git reference"),
):
    """Get file content from GitHub repository."""
    try:
        content = await github_service.get_file_content(url, path, ref)
        return {"path": path, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===================
# Token Management
# ===================

@router.get("/tokens", response_model=List[GitHubTokenResponse])
async def list_github_tokens(
    db: AsyncSession = Depends(get_async_db)
) -> List[GitHubTokenResponse]:
    """List all GitHub/GitLab tokens."""
    tokens = await token_repo.get_active_tokens()
    
    return [
        GitHubTokenResponse(
            id=t.id,
            platform=t.platform,
            domain=t.domain,
            token=mask_token(t.token),
            created_at=t.created_at.isoformat(),
            is_active=t.is_active,
        )
        for t in tokens
    ]


@router.post("/tokens", response_model=GitHubTokenResponse, status_code=201)
async def add_github_token(
    data: GitHubTokenCreate,
    db: AsyncSession = Depends(get_async_db)
) -> GitHubTokenResponse:
    """Add a new GitHub/GitLab token."""
    token_id = str(uuid.uuid4())
    
    token = await token_repo.create_token(
        token_id=token_id,
        platform=data.platform,
        domain=data.domain,
        token=data.token,
    )
    
    return GitHubTokenResponse(
        id=token.id,
        platform=token.platform,
        domain=token.domain,
        token=mask_token(token.token),
        created_at=token.created_at.isoformat(),
        is_active=token.is_active,
    )


@router.delete("/tokens/{token_id}")
async def delete_github_token(
    token_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Delete a GitHub/GitLab token."""
    success = await token_repo.delete_token(token_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Token not found")
    
    return {"status": "deleted", "id": token_id}


@router.get("/user/repos", response_model=List[RepoInfoResponse])
async def list_user_repos(
    query: Optional[str] = None,
    page: int = 1,
    db: AsyncSession = Depends(get_async_db),
) -> List[RepoInfoResponse]:
    """List user's GitHub repositories."""
    # Get the active GitHub token
    token_record = await token_repo.get_latest_token(platform="GitHub")
    
    if not token_record:
        raise HTTPException(
            status_code=400, 
            detail="Failed to load repositories. Please check your GitHub token."
        )
    
    # Create a service instance with the user's token
    service = GitHubService(token=token_record.token)
    
    try:
        repos = await service.list_user_repos(query=query, page=page)
        return [
            RepoInfoResponse(
                name=r.name,
                owner=r.owner,
                full_name=r.full_name,
                url=r.url,
                default_branch=r.default_branch,
                description=r.description,
                is_private=r.is_private,
            )
            for r in repos
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
