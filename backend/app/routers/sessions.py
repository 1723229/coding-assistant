"""
Session management REST API.

Provides endpoints for managing coding assistant sessions.
"""

import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_db
from app.db.schemas import SessionCreate, SessionUpdate, SessionResponse, MessageResponse
from app.db.repository import SessionRepository, MessageRepository
from app.config import get_settings
from app.utils import BaseResponse, NotFoundError

router = APIRouter()
settings = get_settings()

# Repository instances
session_repo = SessionRepository()
message_repo = MessageRepository()


@router.get("/", response_model=List[SessionResponse])
async def list_sessions(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records"),
    db: AsyncSession = Depends(get_async_db)
) -> List[SessionResponse]:
    """List all active sessions with pagination."""
    sessions = await session_repo.get_active_sessions(skip=skip, limit=limit)
    return [
        SessionResponse(
            id=s.id,
            name=s.name,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
            is_active=s.is_active,
            workspace_path=s.workspace_path,
            container_id=s.container_id,
            github_repo_url=s.github_repo_url,
            github_branch=s.github_branch,
        )
        for s in sessions
    ]


@router.post("/", response_model=SessionResponse, status_code=201)
async def create_session(
    data: SessionCreate,
    db: AsyncSession = Depends(get_async_db)
) -> SessionResponse:
    """Create a new session with Docker container and optional repo clone."""
    from app.services import docker_service
    from app.services.github_service import GitHubService
    from app.db.repository import GitHubTokenRepository
    
    session_id = str(uuid.uuid4())
    workspace_path = str(settings.workspace_base_path / session_id)
    
    # Create session in database
    session = await session_repo.create_session(
        session_id=session_id,
        name=data.name or "New Session",
        workspace_path=workspace_path,
        github_repo_url=data.github_repo_url,
        github_branch=data.github_branch or "main",
    )
    
    try:
        # Create Docker container
        container_info = await docker_service.create_workspace(
            session_id=session_id,
            workspace_path=workspace_path
        )
        await session_repo.update_session(session_id, container_id=container_info.id)
        
        # Clone repository in container if provided
        if data.github_repo_url:
            try:
                # Get GitHub token
                token_repo = GitHubTokenRepository()
                token_record = await token_repo.get_latest_token(platform="GitHub")
                
                service = GitHubService(token=token_record.token if token_record else None)
                await service.clone_repo(
                    repo_url=data.github_repo_url,
                    target_path=workspace_path,
                    branch=data.github_branch,
                )
            except Exception as clone_error:
                # Log error but don't fail session creation
                print(f"Failed to clone repo: {clone_error}")
        
        # Refresh session data
        session = await session_repo.get_session_by_id(session_id)
        
    except Exception as e:
        # If container creation fails, session still exists but without container
        print(f"Failed to create container: {e}")
    
    return SessionResponse(
        id=session.id,
        name=session.name,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
        is_active=session.is_active,
        workspace_path=session.workspace_path,
        container_id=session.container_id,
        github_repo_url=session.github_repo_url,
        github_branch=session.github_branch,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_async_db)
) -> SessionResponse:
    """Get a specific session by ID."""
    session = await session_repo.get_session_by_id(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionResponse(
        id=session.id,
        name=session.name,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
        is_active=session.is_active,
        workspace_path=session.workspace_path,
        container_id=session.container_id,
        github_repo_url=session.github_repo_url,
        github_branch=session.github_branch,
    )


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    data: SessionUpdate,
    db: AsyncSession = Depends(get_async_db)
) -> SessionResponse:
    """Update a session."""
    # Build update dict from non-None values
    update_data = {}
    if data.name is not None:
        update_data["name"] = data.name
    if data.github_repo_url is not None:
        update_data["github_repo_url"] = data.github_repo_url
    if data.github_branch is not None:
        update_data["github_branch"] = data.github_branch
    
    session = await session_repo.update_session(session_id, **update_data)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionResponse(
        id=session.id,
        name=session.name,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
        is_active=session.is_active,
        workspace_path=session.workspace_path,
        container_id=session.container_id,
        github_repo_url=session.github_repo_url,
        github_branch=session.github_branch,
    )


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Soft delete a session."""
    success = await session_repo.soft_delete_session(session_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"status": "deleted", "session_id": session_id}


@router.get("/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(
    session_id: str,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records"),
    db: AsyncSession = Depends(get_async_db)
) -> List[MessageResponse]:
    """Get messages for a session."""
    messages = await message_repo.get_session_messages(
        session_id=session_id,
        skip=skip,
        limit=limit,
    )
    
    return [
        MessageResponse(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            content=m.content,
            created_at=m.created_at.isoformat(),
            tool_name=m.tool_name,
        )
        for m in messages
    ]
