"""
Project Service

业务逻辑层 - Project operations
"""

import logging
from typing import Optional
from fastapi import Query

from app.config.logging_config import log_print
from app.utils.model.response_model import BaseResponse, ListResponse
from app.db.repository import ProjectRepository
from app.db.schemas import ProjectCreate, ProjectUpdate, ProjectResponse

logger = logging.getLogger(__name__)


class ProjectService:
    """
    项目服务类

    提供项目相关的所有业务逻辑操作
    """

    def __init__(self):
        self.project_repo = ProjectRepository()

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
        """删除项目"""
        try:
            project = await self.project_repo.delete_project(project_id=project_id)
            if not project:
                return BaseResponse.not_found(message=f"项目 ID {project_id} 不存在")

            return BaseResponse.success(message="项目删除成功")
        except Exception as e:
            logger.error(f"删除项目失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"删除项目失败: {str(e)}")
