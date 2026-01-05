"""
Project Repository

数据访问层 - Project CRUD operations
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.project import Project
from app.db.schemas.project import ProjectCreate, ProjectUpdate
from app.db.repository.base_repository import BaseRepository
from app.db.session import async_with_session


class ProjectRepository(BaseRepository[Project, ProjectCreate, ProjectUpdate]):
    """Project repository with specialized queries"""

    def __init__(self):
        super().__init__(Project)

    @async_with_session
    async def get_project_by_id(self, session: AsyncSession, project_id: int) -> Optional[Project]:
        """Get project by ID"""
        return await self.get_by_id(session, project_id)

    @async_with_session
    async def get_project_by_code(self, session: AsyncSession, code: str) -> Optional[Project]:
        """Get project by code (case-insensitive)"""
        stmt = select(Project).where(Project.code == code.upper())
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @async_with_session
    async def get_projects_by_owner(
        self,
        session: AsyncSession,
        owner: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Project]:
        """Get all projects owned by a user"""
        return await self.get_multi(
            session,
            skip=skip,
            limit=limit,
            filters={"owner": owner},
            order_by="-create_time"
        )

    @async_with_session
    async def create_project(
        self,
        session: AsyncSession,
        data: ProjectCreate,
        created_by: Optional[str] = None
    ) -> Project:
        """Create a new project"""
        return await self.create(session, data, create_by=created_by)

    @async_with_session
    async def update_project(
        self,
        session: AsyncSession,
        project_id: int,
        data: ProjectUpdate,
        updated_by: Optional[str] = None
    ) -> Optional[Project]:
        """Update project"""
        project = await self.get_by_id(session, project_id)
        if not project:
            return None
        return await self.update(session, project, data, update_by=updated_by)

    @async_with_session
    async def delete_project(self, session: AsyncSession, project_id: int) -> Optional[Project]:
        """Delete project"""
        return await self.delete(session, project_id)

    @async_with_session
    async def list_projects(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 50
    ) -> List[Project]:
        """List all projects with pagination"""
        return await self.get_multi(
            session,
            skip=skip,
            limit=limit,
            order_by="-create_time"
        )

    @async_with_session
    async def count_projects(self, session: AsyncSession, owner: Optional[str] = None) -> int:
        """Count projects, optionally by owner"""
        filters = {"owner": owner} if owner else None
        return await self.count(session, filters=filters)
