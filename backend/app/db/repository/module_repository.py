"""
Module Repository

数据访问层 - Module CRUD operations with tree structure support
"""

from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.module import Module
from app.db.schemas.module import ModuleCreate, ModuleUpdate
from app.db.repository.base_repository import BaseRepository
from app.db.session import async_with_session


class ModuleRepository(BaseRepository[Module, ModuleCreate, ModuleUpdate]):
    """Module repository with tree structure support"""

    def __init__(self):
        super().__init__(Module)

    @async_with_session
    async def get_module_by_id(self, session: AsyncSession, module_id: int) -> Optional[Module]:
        """Get module by ID"""
        return await self.get_by_id(session, module_id)

    @async_with_session
    async def get_module_by_code(
        self,
        session: AsyncSession,
        project_id: int,
        is_active: int,
        code: str
    ) -> Optional[Module]:
        """Get module by project_id and code (unique constraint)"""
        stmt = select(Module).where(
            Module.project_id == project_id,
            Module.is_active == is_active,
            Module.code == code
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @async_with_session
    async def get_module_by_session_id(
        self,
        session: AsyncSession,
        session_id: str
    ) -> Optional[Module]:
        """Get POINT type module by session_id"""
        stmt = select(Module).where(Module.session_id == session_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @async_with_session
    async def get_modules_by_project(
        self,
        session: AsyncSession,
        project_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Module]:
        """Get all modules for a project"""
        return await self.get_multi(
            session,
            skip=skip,
            limit=limit,
            filters={"project_id": project_id},
            order_by="id"
        )

    @async_with_session
    async def get_root_modules(
        self,
        session: AsyncSession,
        project_id: int
    ) -> List[Module]:
        """Get root modules (parent_id is None) for a project"""
        stmt = select(Module).where(
            Module.project_id == project_id,
            Module.parent_id.is_(None)
        ).order_by(Module.id)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @async_with_session
    async def get_children_modules(
        self,
        session: AsyncSession,
        parent_id: int
    ) -> List[Module]:
        """Get child modules for a parent module"""
        return await self.get_multi(
            session,
            filters={"parent_id": parent_id},
            order_by="id"
        )

    @async_with_session
    async def create_module(
        self,
        session: AsyncSession,
        data: ModuleCreate,
        created_by: Optional[str] = None
    ) -> Module:
        """Create a new module"""
        return await self.create(session, data, create_by=created_by)

    @async_with_session
    async def update_module(
        self,
        session: AsyncSession,
        module_id: int,
        data: ModuleUpdate,
        updated_by: Optional[str] = None
    ) -> Optional[Module]:
        """Update module"""
        module = await self.get_by_id(session, module_id)
        if not module:
            return None
        return await self.update(session, module, data, update_by=updated_by)

    @async_with_session
    async def delete_module(self, session: AsyncSession, module_id: int) -> Optional[Module]:
        """Delete module (cascade will handle children)"""
        return await self.delete(session, module_id)

    @async_with_session
    async def count_modules(self, session: AsyncSession, project_id: int) -> int:
        """Count modules for a project"""
        return await self.count(session, filters={"project_id": project_id})

    async def build_module_tree(self, project_id: int) -> List[Dict]:
        """Build hierarchical tree structure for all modules in a project"""
        # Get all modules for the project
        all_modules = await self.get_modules_by_project(project_id=project_id, limit=1000)

        # Build a map of module_id -> module
        module_map = {m.id: m for m in all_modules}

        # Build tree structure
        tree = []
        for module in all_modules:
            if module.parent_id is None:
                # Root module
                tree.append(self._build_subtree(module, module_map))

        return tree

    def _build_subtree(self, module: Module, module_map: Dict[int, Module]) -> Dict:
        """Recursively build subtree for a module"""
        node = {
            "id": module.id,
            "project_id": module.project_id,
            "parent_id": module.parent_id,
            "type": module.type.value,
            "name": module.name,
            "code": module.code,
            "url": module.url,
            "require_content": module.require_content,
            "preview_url": module.preview_url,
            "branch": module.branch,
            "session_id": module.session_id,
            "workspace_path": module.workspace_path,
            "container_id": module.container_id,
            "latest_commit_id": module.latest_commit_id,
            "is_active": module.is_active,
            "children": []
        }

        # Find children
        for mid, m in module_map.items():
            if m.parent_id == module.id:
                node["children"].append(self._build_subtree(m, module_map))

        return node
