"""GitHub integration REST API."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..database import get_db
from ..models import Session, Repository, GitHubToken
from ..services.github_service import github_service, GitHubService

router = APIRouter()


class CloneRepoRequest(BaseModel):
    """Request to clone a repository."""
    repo_url: str
    branch: Optional[str] = None


class CommitRequest(BaseModel):
    """Request to commit changes."""
    message: str
    files: Optional[list[str]] = None


class PushRequest(BaseModel):
    """Request to push changes."""
    remote: str = "origin"
    branch: Optional[str] = None


class CreateBranchRequest(BaseModel):
    """Request to create a branch."""
    branch_name: str
    checkout: bool = True


class CreatePRRequest(BaseModel):
    """Request to create a pull request."""
    title: str
    body: str
    head_branch: str
    base_branch: Optional[str] = None


class RepoInfoResponse(BaseModel):
    """Repository information response."""
    name: str
    owner: str
    full_name: str
    url: str
    default_branch: str
    description: Optional[str]
    is_private: bool


class FileChangeResponse(BaseModel):
    """File change response."""
    path: str
    status: str


class PRResponse(BaseModel):
    """Pull request response."""
    number: int
    title: str
    url: str
    state: str
    head_branch: str
    base_branch: str


class GitHubTokenCreate(BaseModel):
    """Request to create/add a GitHub token."""
    platform: str  # "GitHub" | "GitLab"
    domain: str = "github.com"
    token: str


class GitHubTokenResponse(BaseModel):
    """GitHub token response (masked)."""
    id: str
    platform: str
    domain: str
    token: str  # Masked
    created_at: str
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/repo/info")
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
    db: AsyncSession = Depends(get_db),
):
    """Clone a GitHub repository to session workspace."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.workspace_path:
        raise HTTPException(status_code=400, detail="Session has no workspace")
    
    try:
        await github_service.clone_repo(
            repo_url=data.repo_url,
            target_path=session.workspace_path,
            branch=data.branch,
        )
        
        # Update session with GitHub info
        session.github_repo_url = data.repo_url
        session.github_branch = data.branch or "main"
        await db.commit()
        
        return {
            "status": "cloned",
            "repo_url": data.repo_url,
            "workspace_path": session.workspace_path,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/changes")
async def get_changes(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[FileChangeResponse]:
    """Get local changes in repository."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session or not session.workspace_path:
        raise HTTPException(status_code=404, detail="Session or workspace not found")
    
    try:
        changes = await github_service.get_local_changes(session.workspace_path)
        return [
            FileChangeResponse(path=c.path, status=c.status)
            for c in changes
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/commit")
async def commit_changes(
    session_id: str,
    data: CommitRequest,
    db: AsyncSession = Depends(get_db),
):
    """Commit changes to local repository."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
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
    db: AsyncSession = Depends(get_db),
):
    """Push committed changes to GitHub."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session or not session.workspace_path:
        raise HTTPException(status_code=404, detail="Session or workspace not found")
    
    try:
        await github_service.push_changes(
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
    db: AsyncSession = Depends(get_db),
):
    """Create a new branch."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session or not session.workspace_path:
        raise HTTPException(status_code=404, detail="Session or workspace not found")
    
    try:
        await github_service.create_branch(
            repo_path=session.workspace_path,
            branch_name=data.branch_name,
            checkout=data.checkout,
        )
        
        if data.checkout:
            session.github_branch = data.branch_name
            await db.commit()
        
        return {"status": "created", "branch": data.branch_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/branches")
async def list_branches(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    """List branches in repository."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session or not session.workspace_path:
        raise HTTPException(status_code=404, detail="Session or workspace not found")
    
    try:
        branches = await github_service.list_branches(session.workspace_path)
        return branches
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/checkout")
async def checkout_branch(
    session_id: str,
    branch: str = Query(..., description="Branch to checkout"),
    db: AsyncSession = Depends(get_db),
):
    """Checkout a branch."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session or not session.workspace_path:
        raise HTTPException(status_code=404, detail="Session or workspace not found")
    
    try:
        await github_service.checkout_branch(session.workspace_path, branch)
        session.github_branch = branch
        await db.commit()
        return {"status": "checked out", "branch": branch}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/pull")
async def pull_changes(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Pull changes from remote."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session or not session.workspace_path:
        raise HTTPException(status_code=404, detail="Session or workspace not found")
    
    try:
        await github_service.pull_changes(session.workspace_path)
        return {"status": "pulled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/pr")
async def create_pull_request(
    session_id: str,
    data: CreatePRRequest,
    db: AsyncSession = Depends(get_db),
) -> PRResponse:
    """Create a pull request on GitHub."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
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


# GitHub Token Management Endpoints

def mask_token(token: str) -> str:
    """Mask token for display (show first 4 and last 4 characters)."""
    if len(token) <= 8:
        return "****"
    return f"{token[:4]}{'*' * (len(token) - 8)}{token[-4:]}"


@router.get("/tokens")
async def list_github_tokens(
    db: AsyncSession = Depends(get_db)
) -> list[GitHubTokenResponse]:
    """List all GitHub/GitLab tokens."""
    result = await db.execute(
        select(GitHubToken).where(GitHubToken.is_active == True).order_by(GitHubToken.created_at.desc())
    )
    tokens = result.scalars().all()
    
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


@router.post("/tokens")
async def add_github_token(
    data: GitHubTokenCreate,
    db: AsyncSession = Depends(get_db)
) -> GitHubTokenResponse:
    """Add a new GitHub/GitLab token."""
    token_id = str(uuid.uuid4())
    
    token = GitHubToken(
        id=token_id,
        platform=data.platform,
        domain=data.domain,
        token=data.token,
    )
    
    db.add(token)
    await db.commit()
    await db.refresh(token)
    
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
    db: AsyncSession = Depends(get_db)
):
    """Delete a GitHub/GitLab token."""
    result = await db.execute(
        select(GitHubToken).where(GitHubToken.id == token_id)
    )
    token = result.scalar_one_or_none()
    
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    
    await db.delete(token)
    await db.commit()
    
    return {"status": "deleted", "id": token_id}


@router.get("/user/repos")
async def list_user_repos(
    query: Optional[str] = None,
    page: int = 1,
) -> list[RepoInfoResponse]:
    """List user's GitHub repositories."""
    try:
        # Use GitHub API to list user repos
        repos = await github_service.list_user_repos(query=query, page=page)
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

