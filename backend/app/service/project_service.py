"""
Project Service

业务逻辑层 - Project operations with workspace and container management
"""

import uuid
import logging
from typing import Optional
from pathlib import Path
from fastapi import Query

from app.config.logging_config import log_print
from app.config import get_settings
from app.utils.model.response_model import BaseResponse, ListResponse
from app.db.repository import ProjectRepository
from app.db.schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from app.core.docker_service import docker_service
from app.core.github_service import GitHubService

logger = logging.getLogger(__name__)
settings = get_settings()


class ProjectService:
    """
    项目服务类

    提供项目相关的所有业务逻辑操作
    集成工作空间管理、代码拉取、容器创建等功能
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
        """
        创建新项目

        流程：
        1. 检查项目代码是否已存在
        2. 生成 session_id 和 workspace_path
        3. 创建数据库记录
        4. 创建 Docker 容器
        5. 克隆 GitHub 仓库
        6. 更新项目状态
        """
        try:
            # 1. Check if project code already exists
            existing = await self.project_repo.get_project_by_code(code=data.code)
            if existing:
                return BaseResponse.error(message=f"项目代码 '{data.code}' 已存在")

            # 2. Generate session_id and workspace_path
            session_id = str(uuid.uuid4())
            workspace_path = str(settings.workspace_base_path / session_id)

            logger.info(f"Creating project with session_id: {session_id}")

            # 3. Create database record
            project = await self.project_repo.create_project(
                data={
                    "code": data.code,
                    "name": data.name,
                    "codebase": data.codebase,
                    "token": data.token,
                    "owner": data.owner,
                    "session_id": session_id,
                    "workspace_path": workspace_path,
                    "branch": data.branch or "main",
                    "is_active": 1,
                },
                created_by=created_by
            )

            project_id = project.id
            logger.info(f"Project created in database: {project_id}")

            # 4. Create Docker container (optional, non-blocking)
            # try:
            #     logger.info(f"Creating Docker container for project: {project_id}")
            #     container_info = await docker_service.create_workspace(
            #         session_id=session_id,
            #         workspace_path=workspace_path
            #     )
            #     await self.project_repo.update_project(
            #         project_id=project_id,
            #         data={"container_id": container_info.id}
            #     )
            #     logger.info(f"Docker container created: {container_info.id}")
            # except Exception as e:
            #     logger.warning(f"Failed to create container for project {project_id}: {e}")
            #     # Continue even if container creation fails

            # 5. Clone GitHub repository
            if data.codebase:
                try:
                    logger.info(f"Cloning repository: {data.codebase}")
                    service = GitHubService(token=data.token)
                    await service.clone_repo(
                        repo_url=data.codebase,
                        target_path=workspace_path,
                        branch=data.branch,
                    )
                    logger.info(f"Repository cloned successfully to: {workspace_path}")
                except Exception as e:
                    logger.error(f"Failed to clone repo for project {project_id}: {e}")
                    # Mark project as inactive if clone fails
                    await self.project_repo.update_project(
                        project_id=project_id,
                        data={"is_active": 0}
                    )
                    return BaseResponse.error(
                        message=f"项目创建成功，但代码拉取失败: {str(e)}"
                    )

            # 6. Refresh project data
            project = await self.project_repo.get_project_by_id(project_id=project_id)

            return BaseResponse.success(
                data=ProjectResponse.model_validate(project),
                message="项目创建成功，代码已拉取"
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
    async def get_project_by_session_id(self, session_id: str):
        """根据 session_id 获取项目"""
        try:
            project = await self.project_repo.get_project_by_session_id(session_id=session_id)
            if not project:
                return BaseResponse.not_found(message=f"Session ID '{session_id}' 对应的项目不存在")

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
        """删除项目及其关联资源"""
        try:
            project = await self.project_repo.get_project_by_id(project_id=project_id)
            if not project:
                return BaseResponse.not_found(message=f"项目 ID {project_id} 不存在")

            # Clean up container if exists
            if project.container_id:
                try:
                    await docker_service.stop_container(project.container_id)
                    logger.info(f"Stopped container: {project.container_id}")
                except Exception as e:
                    logger.warning(f"Failed to stop container: {e}")

            # Clean up workspace directory
            if project.workspace_path:
                try:
                    import shutil
                    workspace = Path(project.workspace_path)
                    if workspace.exists():
                        shutil.rmtree(workspace)
                        logger.info(f"Removed workspace: {project.workspace_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove workspace: {e}")

            # Delete project from database
            await self.project_repo.delete_project(project_id=project_id)

            return BaseResponse.success(message="项目删除成功")
        except Exception as e:
            logger.error(f"删除项目失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"删除项目失败: {str(e)}")

    @log_print
    async def pull_project_code(self, project_id: int):
        """拉取项目最新代码"""
        try:
            project = await self.project_repo.get_project_by_id(project_id=project_id)
            if not project:
                return BaseResponse.not_found(message=f"项目 ID {project_id} 不存在")

            if not project.workspace_path:
                return BaseResponse.error(message="项目没有工作空间路径")

            # Pull latest code
            service = GitHubService(token=project.token)
            from git import Repo

            workspace = Path(project.workspace_path)
            if not workspace.exists() or not (workspace / ".git").exists():
                return BaseResponse.error(message="工作空间不存在或不是Git仓库")

            repo = Repo(project.workspace_path)
            origin = repo.remotes.origin
            origin.pull()

            return BaseResponse.success(message="代码拉取成功")
        except Exception as e:
            logger.error(f"拉取代码失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"拉取代码失败: {str(e)}")

    @log_print
    async def restart_project_container(self, project_id: int):
        """重启项目容器"""
        try:
            project = await self.project_repo.get_project_by_id(project_id=project_id)
            if not project:
                return BaseResponse.not_found(message=f"项目 ID {project_id} 不存在")

            if not project.container_id:
                return BaseResponse.error(message="项目没有关联的容器")

            # Restart container
            await docker_service.restart_container(project.container_id)

            return BaseResponse.success(message="容器重启成功")
        except Exception as e:
            logger.error(f"重启容器失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"重启容器失败: {str(e)}")
