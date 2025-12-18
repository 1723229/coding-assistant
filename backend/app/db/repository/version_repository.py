"""
Version Repository

数据访问层 - Version CRUD operations
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.version import Version
from app.db.schemas.version import VersionCreate, VersionUpdate
from app.db.repository.base_repository import BaseRepository
from app.db.session import async_with_session


class VersionRepository(BaseRepository[Version, VersionCreate, VersionUpdate]):
    """Version repository with specialized queries"""

    def __init__(self):
        super().__init__(Version)

    @async_with_session
    async def get_version_by_id(self, session: AsyncSession, version_id: int) -> Optional[Version]:
        """Get version by ID"""
        return await self.get_by_id(session, version_id)

    @async_with_session
    async def get_version_by_code(
        self,
        session: AsyncSession,
        module_id: int,
        code: str
    ) -> Optional[Version]:
        """Get version by module and version code"""
        stmt = select(Version).where(
            Version.module_id == module_id,
            Version.code == code
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @async_with_session
    async def get_version_by_commit(
        self,
        session: AsyncSession,
        module_id: int,
        commit: str
    ) -> Optional[Version]:
        """Get version by module and commit hash"""
        stmt = select(Version).where(
            Version.module_id == module_id,
            Version.commit == commit.lower()
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @async_with_session
    async def get_versions_by_module(
        self,
        session: AsyncSession,
        module_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[Version]:
        """Get all versions for a module"""
        return await self.get_multi(
            session,
            skip=skip,
            limit=limit,
            filters={"module_id": module_id},
            order_by="-create_time"
        )

    @async_with_session
    async def create_version(
        self,
        session: AsyncSession,
        data: VersionCreate,
        created_by: Optional[str] = None
    ) -> Version:
        """Create a new version"""
        return await self.create(session, data, create_by=created_by)

    @async_with_session
    async def update_version(
        self,
        session: AsyncSession,
        version_id: int,
        data: VersionUpdate,
        updated_by: Optional[str] = None
    ) -> Optional[Version]:
        """Update version"""
        version = await self.get_by_id(session, version_id)
        if not version:
            return None
        return await self.update(session, version, data, update_by=updated_by)

    @async_with_session
    async def delete_version(self, session: AsyncSession, version_id: int) -> Optional[Version]:
        """Delete version"""
        return await self.delete(session, version_id)

    @async_with_session
    async def count_versions(self, session: AsyncSession, module_id: int) -> int:
        """Count versions for a module"""
        return await self.count(session, filters={"module_id": module_id})

    @async_with_session
    async def get_latest_version(
        self,
        session: AsyncSession,
        module_id: int
    ) -> Optional[Version]:
        """Get the most recent version for a module"""
        stmt = select(Version).where(
            Version.module_id == module_id
        ).order_by(Version.create_time.desc()).limit(1)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @async_with_session
    async def count_running_containers(self, session: AsyncSession) -> int:
        """
        统计当前运行中的容器数量

        运行中的容器对应的状态：
        - SPEC_GENERATING: Spec生成中
        - CODE_BUILDING: 代码构建中

        Returns:
            运行中的容器数量
        """
        from app.db.models.version import VersionStatus
        from sqlalchemy import func

        stmt = select(func.count(Version.id)).where(
            Version.status.in_([
                VersionStatus.SPEC_GENERATING.value,
                VersionStatus.SPEC_GENERATED.value,
                VersionStatus.CODE_BUILDING.value
            ])
        )
        result = await session.execute(stmt)
        return result.scalar() or 0

    @async_with_session
    async def get_version_by_module_and_status(
        self,
        session: AsyncSession,
        module_id: int,
        status: str
    ) -> Optional[Version]:
        """
        根据 module_id 和状态获取 Version

        Args:
            module_id: 模块ID
            status: 版本状态

        Returns:
            Version 对象或 None
        """
        stmt = select(Version).where(
            Version.module_id == module_id,
            Version.status == status
        ).order_by(Version.create_time.desc()).limit(1)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
