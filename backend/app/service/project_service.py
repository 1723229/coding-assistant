"""
Project Service

业务逻辑层 - Project CRUD operations only
"""

import logging
from typing import Optional
from fastapi import Query

from app.config.logging_config import log_print
from app.utils.model.response_model import BaseResponse, ListResponse
from app.db.repository import ProjectRepository, ModuleRepository
from app.db.schemas import ProjectCreate, ProjectUpdate, ProjectResponse

logger = logging.getLogger(__name__)


class ProjectService:
    """
    项目服务类

    提供项目相关的基本 CRUD 操作
    """

    def __init__(self):
        self.project_repo = ProjectRepository()
        self.module_repo = ModuleRepository()

    @log_print
    async def list_projects(
        self,
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(50, ge=1, le=100, description="Maximum number of records"),
        owner: Optional[int] = None,
    ):
        """获取项目列表"""
        try:
            if owner:
                projects = await self.project_repo.get_projects_by_owner(
                    owner=owner,
                    skip=skip,
                    limit=limit
                )
                total = await self.project_repo.count_projects(owner=owner)
            else:
                projects = await self.project_repo.list_projects(skip=skip, limit=limit)
                total = await self.project_repo.count_projects()

            items = [ProjectResponse.model_validate(p) for p in projects]
            return ListResponse.success(items=items, total=total)
        except Exception as e:
            logger.error(f"获取项目列表失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"获取项目列表失败: {str(e)}")

    @log_print
    async def create_project(self, data: ProjectCreate, created_by: Optional[str] = None):
        """创建新项目"""
        try:
            # Check if project code already exists
            existing = await self.project_repo.get_project_by_code(code=data.code)
            if existing:
                return BaseResponse.error(message=f"项目代码 '{data.code}' 已存在")

            # Create project in database
            project = await self.project_repo.create_project(
                data=data,
                created_by=created_by
            )

            return BaseResponse.success(
                data=ProjectResponse.model_validate(project),
                message="项目创建成功"
            )

        except Exception as e:
            logger.error(f"创建项目失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"创建项目失败: {str(e)}")

    @log_print
    async def get_project(self, project_id: int):
        """获取项目详情"""
        try:
            project = await self.project_repo.get_project_by_id(project_id=project_id)
            if not project:
                return BaseResponse.not_found(message=f"项目 ID {project_id} 不存在")

            return BaseResponse.success(
                data=ProjectResponse.model_validate(project),
                message="获取项目详情成功"
            )
        except Exception as e:
            logger.error(f"获取项目详情失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"获取项目详情失败: {str(e)}")

    @log_print
    async def get_project_by_code(self, code: str):
        """根据项目代码获取项目"""
        try:
            project = await self.project_repo.get_project_by_code(code=code)
            if not project:
                return BaseResponse.not_found(message=f"项目代码 '{code}' 不存在")

            return BaseResponse.success(
                data=ProjectResponse.model_validate(project),
                message="获取项目详情成功"
            )
        except Exception as e:
            logger.error(f"获取项目详情失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"获取项目详情失败: {str(e)}")

    @log_print
    async def update_project(
        self,
        project_id: int,
        data: ProjectUpdate,
        updated_by: Optional[str] = None
    ):
        """更新项目信息"""
        try:
            # Check if project exists
            existing = await self.project_repo.get_project_by_id(project_id=project_id)
            if not existing:
                return BaseResponse.not_found(message=f"项目 ID {project_id} 不存在")

            # If updating code, check for duplicates
            if data.code and data.code != existing.code:
                duplicate = await self.project_repo.get_project_by_code(code=data.code)
                if duplicate:
                    return BaseResponse.error(message=f"项目代码 '{data.code}' 已存在")

            project = await self.project_repo.update_project(
                project_id=project_id,
                data=data,
                updated_by=updated_by
            )
            return BaseResponse.success(
                data=ProjectResponse.model_validate(project),
                message="项目更新成功"
            )
        except Exception as e:
            logger.error(f"更新项目失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"更新项目失败: {str(e)}")

    @log_print
    async def delete_project(self, project_id: int):
        """
        删除项目（递归删除所有模块及其资源）

        清理内容：
        1. 递归删除所有模块（调用 ModuleService.delete_module）
        2. 每个模块的删除会级联清理：
           - 子模块
           - framework 数据库中的 sys_module 记录
           - POINT 类型模块的容器
           - 工作空间目录
           - 版本记录（更新状态为 DELETED）
        3. 删除项目数据库记录
        """
        try:
            project = await self.project_repo.get_project_by_id(project_id=project_id)
            if not project:
                return BaseResponse.not_found(message=f"项目 ID {project_id} 不存在")

            logger.info(f"Deleting project: {project.name} (ID: {project_id})")

            # 1. 获取项目下的所有根模块（parent_id 为 None）
            root_modules = await self.module_repo.get_root_modules(project_id=project_id)

            if root_modules:
                logger.info(f"Found {len(root_modules)} root modules to delete")

                # 导入 ModuleService 来调用递归删除方法
                from app.service.module_service import ModuleService
                module_service = ModuleService()

                # 2. 递归删除每个根模块（会自动删除所有子模块）
                deleted_count = 0
                failed_modules = []

                for module in root_modules:
                    try:
                        logger.info(f"Deleting root module: {module.name} (ID: {module.id})")
                        result = await module_service.delete_module(module_id=module.id)

                        # 检查删除是否成功
                        if result.get('code') == 200:
                            deleted_count += 1
                            logger.info(f"Successfully deleted module tree: {module.name}")
                        else:
                            failed_modules.append(f"{module.name} (ID: {module.id})")
                            logger.warning(f"Failed to delete module {module.name}: {result.get('message')}")

                    except Exception as e:
                        failed_modules.append(f"{module.name} (ID: {module.id})")
                        logger.error(f"Exception while deleting module {module.name}: {e}", exc_info=True)

                if failed_modules:
                    logger.warning(f"Failed to delete {len(failed_modules)} module trees: {', '.join(failed_modules)}")

                logger.info(f"Successfully deleted {deleted_count}/{len(root_modules)} module trees")

            # 3. 删除项目数据库记录
            await self.project_repo.delete_project(project_id=project_id)
            logger.info(f"Deleted project from database: {project.name} (ID: {project_id})")

            return BaseResponse.success(
                message=f"项目 '{project.name}' 及其所有模块、工作空间、容器已成功删除"
            )

        except Exception as e:
            logger.error(f"删除项目失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"删除项目失败: {str(e)}")
