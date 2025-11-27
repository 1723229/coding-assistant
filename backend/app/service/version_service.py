"""
Version Service

业务逻辑层 - Version operations
"""

import logging
from typing import Optional
from fastapi import Query

from app.config.logging_config import log_print
from app.utils.model.response_model import BaseResponse, ListResponse
from app.db.repository import VersionRepository, ProjectRepository
from app.db.schemas import VersionCreate, VersionUpdate, VersionResponse

logger = logging.getLogger(__name__)


class VersionService:
    """
    版本服务类

    提供版本相关的所有业务逻辑操作
    """

    def __init__(self):
        self.version_repo = VersionRepository()
        self.project_repo = ProjectRepository()

    @log_print
    async def list_versions(
        self,
        project_id: int,
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(50, ge=1, le=100, description="Maximum number of records"),
    ):
        """获取项目的版本列表"""
        try:
            # Verify project exists
            project = await self.project_repo.get_project_by_id(project_id=project_id)
            if not project:
                return BaseResponse.not_found(message=f"项目 ID {project_id} 不存在")

            versions = await self.version_repo.get_versions_by_project(
                project_id=project_id,
                skip=skip,
                limit=limit
            )
            total = await self.version_repo.count_versions(project_id=project_id)

            items = [VersionResponse.model_validate(v) for v in versions]
            return ListResponse.success(items=items, total=total)
        except Exception as e:
            logger.error(f"获取版本列表失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"获取版本列表失败: {str(e)}")

    @log_print
    async def create_version(self, data: VersionCreate, created_by: Optional[str] = None):
        """创建新版本"""
        try:
            # Verify project exists
            project = await self.project_repo.get_project_by_id(project_id=data.project_id)
            if not project:
                return BaseResponse.not_found(message=f"项目 ID {data.project_id} 不存在")

            # Check if version code already exists in this project
            existing_code = await self.version_repo.get_version_by_code(
                project_id=data.project_id,
                code=data.code
            )
            if existing_code:
                return BaseResponse.error(
                    message=f"版本编号 '{data.code}' 在项目中已存在"
                )

            # Check if commit hash already exists in this project
            existing_commit = await self.version_repo.get_version_by_commit(
                project_id=data.project_id,
                commit=data.commit
            )
            if existing_commit:
                return BaseResponse.error(
                    message=f"Commit '{data.commit}' 已被记录为版本 '{existing_commit.code}'"
                )

            version = await self.version_repo.create_version(
                data=data,
                created_by=created_by
            )
            return BaseResponse.success(
                data=VersionResponse.model_validate(version),
                message="版本创建成功"
            )
        except Exception as e:
            logger.error(f"创建版本失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"创建版本失败: {str(e)}")

    @log_print
    async def get_version(self, version_id: int):
        """获取版本详情"""
        try:
            version = await self.version_repo.get_version_by_id(version_id=version_id)
            if not version:
                return BaseResponse.not_found(message=f"版本 ID {version_id} 不存在")

            return BaseResponse.success(
                data=VersionResponse.model_validate(version),
                message="获取版本详情成功"
            )
        except Exception as e:
            logger.error(f"获取版本详情失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"获取版本详情失败: {str(e)}")

    @log_print
    async def get_version_by_code(self, project_id: int, code: str):
        """根据版本编号获取版本"""
        try:
            version = await self.version_repo.get_version_by_code(
                project_id=project_id,
                code=code
            )
            if not version:
                return BaseResponse.not_found(
                    message=f"项目 {project_id} 中版本编号 '{code}' 不存在"
                )

            return BaseResponse.success(
                data=VersionResponse.model_validate(version),
                message="获取版本详情成功"
            )
        except Exception as e:
            logger.error(f"获取版本详情失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"获取版本详情失败: {str(e)}")

    @log_print
    async def get_latest_version(self, project_id: int):
        """获取项目的最新版本"""
        try:
            # Verify project exists
            project = await self.project_repo.get_project_by_id(project_id=project_id)
            if not project:
                return BaseResponse.not_found(message=f"项目 ID {project_id} 不存在")

            version = await self.version_repo.get_latest_version(project_id=project_id)
            if not version:
                return BaseResponse.not_found(message=f"项目 ID {project_id} 没有版本记录")

            return BaseResponse.success(
                data=VersionResponse.model_validate(version),
                message="获取最新版本成功"
            )
        except Exception as e:
            logger.error(f"获取最新版本失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"获取最新版本失败: {str(e)}")

    @log_print
    async def update_version(
        self,
        version_id: int,
        data: VersionUpdate,
        updated_by: Optional[str] = None
    ):
        """更新版本信息"""
        try:
            # Check if version exists
            existing = await self.version_repo.get_version_by_id(version_id=version_id)
            if not existing:
                return BaseResponse.not_found(message=f"版本 ID {version_id} 不存在")

            # If updating code, check for duplicates in the same project
            if data.code and data.code != existing.code:
                duplicate = await self.version_repo.get_version_by_code(
                    project_id=existing.project_id,
                    code=data.code
                )
                if duplicate:
                    return BaseResponse.error(
                        message=f"版本编号 '{data.code}' 在项目中已存在"
                    )

            # If updating commit, check for duplicates in the same project
            if data.commit and data.commit != existing.commit:
                duplicate = await self.version_repo.get_version_by_commit(
                    project_id=existing.project_id,
                    commit=data.commit
                )
                if duplicate:
                    return BaseResponse.error(
                        message=f"Commit '{data.commit}' 已被记录为版本 '{duplicate.code}'"
                    )

            version = await self.version_repo.update_version(
                version_id=version_id,
                data=data,
                updated_by=updated_by
            )
            return BaseResponse.success(
                data=VersionResponse.model_validate(version),
                message="版本更新成功"
            )
        except Exception as e:
            logger.error(f"更新版本失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"更新版本失败: {str(e)}")

    @log_print
    async def delete_version(self, version_id: int):
        """删除版本"""
        try:
            version = await self.version_repo.delete_version(version_id=version_id)
            if not version:
                return BaseResponse.not_found(message=f"版本 ID {version_id} 不存在")

            return BaseResponse.success(message="版本删除成功")
        except Exception as e:
            logger.error(f"删除版本失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"删除版本失败: {str(e)}")
