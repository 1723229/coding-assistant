"""Session management REST API."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..database import get_db
from ..models import Session, Message
from ..config import get_settings

router = APIRouter()
settings = get_settings()


class SessionCreate(BaseModel):
    """Request model for creating a session."""
    name: Optional[str] = "New Session"
    github_repo_url: Optional[str] = None
    github_branch: Optional[str] = "main"


class SessionUpdate(BaseModel):
    """Request model for updating a session."""
    name: Optional[str] = None
    github_repo_url: Optional[str] = None
    github_branch: Optional[str] = None


class SessionResponse(BaseModel):
    """Response model for session."""
    id: str
    name: str
    created_at: str
    updated_at: str
    is_active: bool
    workspace_path: Optional[str]
    container_id: Optional[str]
    github_repo_url: Optional[str]
    github_branch: Optional[str]

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Response model for message."""
    id: int
    session_id: str
    role: str
    content: str
    created_at: str
    tool_name: Optional[str]

    class Config:
        from_attributes = True


@router.get("/")
async def list_sessions(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
) -> list[SessionResponse]:
    """List all sessions."""
    result = await db.execute(
        select(Session)
        .where(Session.is_active == True)
        .order_by(Session.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    sessions = result.scalars().all()
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


@router.post("/")
async def create_session(
    data: SessionCreate,
    db: AsyncSession = Depends(get_db)
) -> SessionResponse:
    """Create a new session with Docker container and optional repo clone."""
    from ..services.docker_service import docker_service
    from ..services.github_service import github_service
    
    session_id = str(uuid.uuid4())
    workspace_path = str(settings.workspace_base_path / session_id)
    
    # Create database record
    session = Session(
        id=session_id,
        name=data.name,
        workspace_path=workspace_path,
        github_repo_url=data.github_repo_url,
        github_branch=data.github_branch,
    )
    
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    try:
        # Create Docker container
        container_info = await docker_service.create_workspace(
            session_id=session_id,
            workspace_path=workspace_path
        )
        session.container_id = container_info.id
        
        # Clone repository in container if provided
        if data.github_repo_url:
            try:
                await github_service.clone_repo_in_container(
                    session_id=session_id,
                    repo_url=data.github_repo_url,
                    branch=data.github_branch
                )
            except Exception as clone_error:
                # Log error but don't fail session creation
                print(f"Failed to clone repo in container: {clone_error}")
        
        await db.commit()
        await db.refresh(session)
        
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


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
) -> SessionResponse:
    """Get a specific session."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
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


@router.patch("/{session_id}")
async def update_session(
    session_id: str,
    data: SessionUpdate,
    db: AsyncSession = Depends(get_db)
) -> SessionResponse:
    """Update a session."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if data.name is not None:
        session.name = data.name
    if data.github_repo_url is not None:
        session.github_repo_url = data.github_repo_url
    if data.github_branch is not None:
        session.github_branch = data.github_branch
    
    await db.commit()
    await db.refresh(session)
    
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
    db: AsyncSession = Depends(get_db)
):
    """Soft delete a session."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.is_active = False
    await db.commit()
    
    return {"status": "deleted", "session_id": session_id}


@router.get("/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
) -> list[MessageResponse]:
    """Get messages for a session."""
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    messages = result.scalars().all()
    
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

