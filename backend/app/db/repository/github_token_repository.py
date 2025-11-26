"""
GitHub Token repository implementation

Provides GitHub token-related data access methods.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.github_token import GitHubToken
from app.db.schemas.github import GitHubTokenCreate
from app.db.repository.base_repository import BaseRepository
from app.db.session import async_with_session


class GitHubTokenRepository(BaseRepository[GitHubToken, GitHubTokenCreate, None]):
    """
    GitHub Token data access layer
    
    Provides GitHub token-related database operations.
    """

    def __init__(self):
        super().__init__(GitHubToken)
    
    @async_with_session
    async def get_active_tokens(
        self,
        session: AsyncSession,
        platform: Optional[str] = None
    ) -> List[GitHubToken]:
        """
        Get all active tokens, optionally filtered by platform
        
        Args:
            session: Database session
            platform: Optional platform filter (GitHub, GitLab)
            
        Returns:
            List of active tokens
        """
        stmt = (
            select(GitHubToken)
            .where(GitHubToken.is_active == True)
            .order_by(GitHubToken.created_at.desc())
        )
        
        if platform:
            stmt = stmt.where(GitHubToken.platform == platform)
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    @async_with_session
    async def get_latest_token(
        self,
        session: AsyncSession,
        platform: str = "GitHub"
    ) -> Optional[GitHubToken]:
        """
        Get the latest active token for a platform
        
        Args:
            session: Database session
            platform: Platform name (GitHub, GitLab)
            
        Returns:
            Latest token or None
        """
        stmt = (
            select(GitHubToken)
            .where(
                GitHubToken.is_active == True,
                GitHubToken.platform == platform
            )
            .order_by(GitHubToken.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @async_with_session
    async def create_token(
        self,
        session: AsyncSession,
        token_id: str,
        platform: str,
        domain: str,
        token: str
    ) -> GitHubToken:
        """
        Create a new token
        
        Args:
            session: Database session
            token_id: Token UUID
            platform: Platform name
            domain: Platform domain
            token: Access token
            
        Returns:
            Created token object
        """
        new_token = GitHubToken(
            id=token_id,
            platform=platform,
            domain=domain,
            token=token,
        )
        session.add(new_token)
        await session.flush()
        await session.refresh(new_token)
        return new_token
    
    @async_with_session
    async def delete_token(
        self,
        session: AsyncSession,
        token_id: str
    ) -> bool:
        """
        Delete a token by ID
        
        Args:
            session: Database session
            token_id: Token UUID
            
        Returns:
            True if deleted, False if not found
        """
        stmt = select(GitHubToken).where(GitHubToken.id == token_id)
        result = await session.execute(stmt)
        token = result.scalar_one_or_none()
        
        if not token:
            return False
        
        await session.delete(token)
        await session.flush()
        return True
    
    @async_with_session
    async def deactivate_token(
        self,
        session: AsyncSession,
        token_id: str
    ) -> bool:
        """
        Deactivate a token by ID
        
        Args:
            session: Database session
            token_id: Token UUID
            
        Returns:
            True if deactivated, False if not found
        """
        stmt = select(GitHubToken).where(GitHubToken.id == token_id)
        result = await session.execute(stmt)
        token = result.scalar_one_or_none()
        
        if not token:
            return False
        
        token.is_active = False
        await session.flush()
        return True

