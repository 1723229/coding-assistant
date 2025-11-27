"""
Module Service

业务逻辑层 - Module operations with tree structure support
"""

import logging
from typing import Optional
from fastapi import Query

from app.config.logging_config import log_print
from app.utils.model.response_model import BaseResponse, ListResponse
from app.db.repository import ModuleRepository, ProjectRepository
from app.db.schemas import ModuleCreate, ModuleUpdate, ModuleResponse

logger = logging.getLogger(__name__)


class ModuleService:
    """
    模块服务类

    提供模块相关的所有业务逻辑操作，支持树形结构
    """

    def __init__(self):
        self.module_repo = ModuleRepository()
        self.project_repo = ProjectRepository()

    @log_print
    async def list_modules(
        self,
        project_id: int,
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, le=500, description="Maximum number of records"),
    ):
        """获取项目的模块列表"""
        try:
            # Verify project exists
            project = await self.project_repo.get_project_by_id(project_id=project_id)
            if not project:
                return BaseResponse.not_found(message=f"项目 ID {project_id} 不存在")

            modules = await self.module_repo.get_modules_by_project(
                project_id=project_id,
                skip=skip,
                limit=limit
            )
            total = await self.module_repo.count_modules(project_id=project_id)

            items = [ModuleResponse.model_validate(m) for m in modules]
            return ListResponse.success(items=items, total=total)
        except Exception as e:
            logger.error(f"获取模块列表失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"获取模块列表失败: {str(e)}")

    @log_print
    async def get_module_tree(self, project_id: int):
        """获取项目的模块树形结构"""
        try:
            # Verify project exists
            project = await self.project_repo.get_project_by_id(project_id=project_id)
            if not project:
                return BaseResponse.not_found(message=f"项目 ID {project_id} 不存在")

            tree = await self.module_repo.build_module_tree(project_id=project_id)
            return BaseResponse.success(data=tree, message="获取模块树成功")
        except Exception as e:
            logger.error(f"获取模块树失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"获取模块树失败: {str(e)}")

    @log_print
    async def create_module(self, data: ModuleCreate, created_by: Optional[str] = None):
        """创建新模块"""
        try:
            # Verify project exists
            project = await self.project_repo.get_project_by_id(project_id=data.project_id)
            if not project:
                return BaseResponse.not_found(message=f"项目 ID {data.project_id} 不存在")

            # Check if module code already exists in this project
            existing = await self.module_repo.get_module_by_code(
                project_id=data.project_id,
                code=data.code
            )
            if existing:
                return BaseResponse.error(
                    message=f"模块代码 '{data.code}' 在项目中已存在"
                )

            # Verify parent exists if specified
            if data.parent_id:
                parent = await self.module_repo.get_module_by_id(module_id=data.parent_id)
                if not parent:
                    return BaseResponse.not_found(message=f"父模块 ID {data.parent_id} 不存在")
                if parent.project_id != data.project_id:
                    return BaseResponse.error(message="父模块必须属于同一项目")

            module = await self.module_repo.create_module(
                data=data,
                created_by=created_by
            )
            return BaseResponse.success(
                data=ModuleResponse.model_validate(module),
                message="模块创建成功"
            )
        except Exception as e:
            logger.error(f"创建模块失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"创建模块失败: {str(e)}")

    @log_print
    async def get_module(self, module_id: int):
        """获取模块详情"""
        try:
            module = await self.module_repo.get_module_by_id(module_id=module_id)
            if not module:
                return BaseResponse.not_found(message=f"模块 ID {module_id} 不存在")

            return BaseResponse.success(
                data=ModuleResponse.model_validate(module),
                message="获取模块详情成功"
            )
        except Exception as e:
            logger.error(f"获取模块详情失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"获取模块详情失败: {str(e)}")

    @log_print
    async def update_module(
        self,
        module_id: int,
        data: ModuleUpdate,
        updated_by: Optional[str] = None
    ):
        """更新模块信息"""
        try:
            # Check if module exists
            existing = await self.module_repo.get_module_by_id(module_id=module_id)
            if not existing:
                return BaseResponse.not_found(message=f"模块 ID {module_id} 不存在")

            # If updating code, check for duplicates in the same project
            if data.code and data.code != existing.code:
                duplicate = await self.module_repo.get_module_by_code(
                    project_id=existing.project_id,
                    code=data.code
                )
                if duplicate:
                    return BaseResponse.error(
                        message=f"模块代码 '{data.code}' 在项目中已存在"
                    )

            # Verify new parent if specified
            if data.parent_id is not None:
                if data.parent_id == module_id:
                    return BaseResponse.error(message="模块不能设置自己为父模块")
                parent = await self.module_repo.get_module_by_id(module_id=data.parent_id)
                if not parent:
                    return BaseResponse.not_found(message=f"父模块 ID {data.parent_id} 不存在")
                if parent.project_id != existing.project_id:
                    return BaseResponse.error(message="父模块必须属于同一项目")

            module = await self.module_repo.update_module(
                module_id=module_id,
                data=data,
                updated_by=updated_by
            )
            return BaseResponse.success(
                data=ModuleResponse.model_validate(module),
                message="模块更新成功"
            )
        except Exception as e:
            logger.error(f"更新模块失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"更新模块失败: {str(e)}")

    @log_print
    async def delete_module(self, module_id: int):
        """删除模块（级联删除子模块）"""
        try:
            module = await self.module_repo.delete_module(module_id=module_id)
            if not module:
                return BaseResponse.not_found(message=f"模块 ID {module_id} 不存在")

            return BaseResponse.success(message="模块删除成功")
        except Exception as e:
            logger.error(f"删除模块失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"删除模块失败: {str(e)}")
