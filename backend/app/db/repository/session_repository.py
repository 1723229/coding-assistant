"""
Session repository implementation

Provides session-related data access methods.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.session import Session
from app.db.schemas.session import SessionCreate, SessionUpdate
from app.db.repository.base_repository import BaseRepository
from app.db.session import async_with_session


class SessionRepository(BaseRepository[Session, SessionCreate, SessionUpdate]):
    """
    Session data access layer
    
    Provides session-related database operations.
    """

    def __init__(self):
        super().__init__(Session)
    
    @async_with_session
    async def get_session_by_id(
        self,
        session: AsyncSession,
        session_id: str
    ) -> Optional[Session]:
        """
        Get session by ID
        
        Args:
            session: Database session
            session_id: Session UUID
            
        Returns:
            Session object or None
        """
        stmt = select(Session).where(Session.id == session_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @async_with_session
    async def get_active_sessions(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 50
    ) -> List[Session]:
        """
        Get active sessions with pagination
        
        Args:
            session: Database session
            skip: Number to skip
            limit: Maximum number to return
            
        Returns:
            List of active sessions
        """
        stmt = (
            select(Session)
            .where(Session.is_active == True)
            .order_by(Session.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    @async_with_session
    async def create_session(
        self,
        session: AsyncSession,
        session_id: str,
        name: str = "New Session",
        workspace_path: Optional[str] = None,
        github_repo_url: Optional[str] = None,
        github_branch: str = "main"
    ) -> Session:
        """
        Create a new session
        
        Args:
            session: Database session
            session_id: Session UUID
            name: Session name
            workspace_path: Workspace path
            github_repo_url: GitHub repository URL
            github_branch: GitHub branch
            
        Returns:
            Created session object
        """
        new_session = Session(
            id=session_id,
            name=name,
            workspace_path=workspace_path,
            github_repo_url=github_repo_url,
            github_branch=github_branch,
        )
        session.add(new_session)
        await session.flush()
        await session.refresh(new_session)
        return new_session
    
    @async_with_session
    async def update_session(
        self,
        session: AsyncSession,
        session_id: str,
        **update_data
    ) -> Optional[Session]:
        """
        Update session by ID
        
        Args:
            session: Database session
            session_id: Session UUID
            **update_data: Fields to update
            
        Returns:
            Updated session or None
        """
        stmt = select(Session).where(Session.id == session_id)
        result = await session.execute(stmt)
        db_session = result.scalar_one_or_none()
        
        if not db_session:
            return None
        
        for key, value in update_data.items():
            if hasattr(db_session, key) and value is not None:
                setattr(db_session, key, value)
        
        db_session.touch()
        await session.flush()
        await session.refresh(db_session)
        return db_session
    
    @async_with_session
    async def soft_delete_session(
        self,
        session: AsyncSession,
        session_id: str
    ) -> bool:
        """
        Soft delete a session
        
        Args:
            session: Database session
            session_id: Session UUID
            
        Returns:
            True if deleted, False if not found
        """
        stmt = select(Session).where(Session.id == session_id)
        result = await session.execute(stmt)
        db_session = result.scalar_one_or_none()
        
        if not db_session:
            return False
        
        db_session.is_active = False
        await session.flush()
        return True
    
    @async_with_session
    async def set_container_id(
        self,
        session: AsyncSession,
        session_id: str,
        container_id: str
    ) -> Optional[Session]:
        """
        Set container ID for session
        
        Args:
            session: Database session
            session_id: Session UUID
            container_id: Docker container ID
            
        Returns:
            Updated session or None
        """
        return await self.update_session(session, session_id, container_id=container_id)


