"""
Module Service

业务逻辑层 - Module operations with tree structure support
POINT type modules create sessions and manage workspaces
"""

import uuid
import logging
from typing import Optional
from pathlib import Path
from fastapi import Query

from app.config.logging_config import log_print
from app.config import get_settings
from app.utils.model.response_model import BaseResponse, ListResponse
from app.db.repository import ModuleRepository, ProjectRepository
from app.db.schemas import ModuleCreate, ModuleUpdate, ModuleResponse
from app.db.models.module import ModuleType
from app.core.docker_service import docker_service
from app.core.github_service import GitHubService

logger = logging.getLogger(__name__)
settings = get_settings()


class ModuleService:
    """
    模块服务类

    提供模块相关的所有业务逻辑操作，支持树形结构
    POINT 类型创建 session 和 workspace，拉取代码
    NODE 类型只做功能说明，URL 与子节点共享
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
        """
        创建新模块

        流程：
        - NODE 类型：直接创建数据库记录，URL 与子节点共享
        - POINT 类型：
          1. 检查项目代码唯一性
          2. 生成 session_id 和 workspace_path
          3. 创建数据库记录
          4. 创建 Docker 容器（可选）
          5. 克隆 GitHub 仓库到 workspace
        """
        try:
            # Verify project exists and get project info
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

            # Prepare module data
            module_data = data.model_dump()

            # Handle POINT type: create session and workspace
            if data.type == ModuleType.POINT:
                logger.info(f"Creating POINT type module: {data.code}")

                # 1. Generate session_id and workspace_path
                session_id = str(uuid.uuid4())
                workspace_path = str(settings.workspace_base_path / session_id)

                module_data.update({
                    "session_id": session_id,
                    "workspace_path": workspace_path,
                    "branch": data.branch or "main",
                    "is_active": 1,
                })

                logger.info(f"Module session_id: {session_id}, workspace: {workspace_path}")

                # 2. Create module in database first
                module = await self.module_repo.create_module(
                    data=module_data,
                    created_by=created_by
                )

                module_id = module.id
                logger.info(f"Module created in database: {module_id}")

                # 3. Create Docker container (optional, non-blocking)
                try:
                    logger.info(f"Creating Docker container for module: {module_id}")
                    container_info = await docker_service.create_workspace(
                        session_id=session_id,
                        workspace_path=workspace_path
                    )
                    await self.module_repo.update_module(
                        module_id=module_id,
                        data={"container_id": container_info.id}
                    )
                    logger.info(f"Docker container created: {container_info.id}")
                except Exception as e:
                    logger.warning(f"Failed to create container for module {module_id}: {e}")
                    # Continue even if container creation fails

                # 4. Clone GitHub repository
                if project.codebase:
                    try:
                        logger.info(f"Cloning repository: {project.codebase}")
                        service = GitHubService(token=project.token)
                        await service.clone_repo(
                            repo_url=project.codebase,
                            target_path=workspace_path,
                            branch=module_data.get("branch"),
                        )
                        logger.info(f"Repository cloned successfully to: {workspace_path}")
                    except Exception as e:
                        logger.error(f"Failed to clone repo for module {module_id}: {e}")
                        # Mark module as inactive if clone fails
                        await self.module_repo.update_module(
                            module_id=module_id,
                            data={"is_active": 0}
                        )
                        return BaseResponse.error(
                            message=f"模块创建成功，但代码拉取失败: {str(e)}"
                        )

                # 5. Refresh module data
                module = await self.module_repo.get_module_by_id(module_id=module_id)
                return BaseResponse.success(
                    data=ModuleResponse.model_validate(module),
                    message="POINT 模块创建成功，代码已拉取"
                )

            else:
                # NODE type: simple creation without workspace
                logger.info(f"Creating NODE type module: {data.code}")
                module = await self.module_repo.create_module(
                    data=module_data,
                    created_by=created_by
                )
                return BaseResponse.success(
                    data=ModuleResponse.model_validate(module),
                    message="NODE 模块创建成功"
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
    async def get_module_by_session_id(self, session_id: str):
        """根据 session_id 获取模块（仅 POINT 类型）"""
        try:
            module = await self.module_repo.get_module_by_session_id(session_id=session_id)
            if not module:
                return BaseResponse.not_found(message=f"Session ID '{session_id}' 对应的模块不存在")

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
        """删除模块（级联删除子模块，清理 POINT 类型的 workspace 和容器）"""
        try:
            module = await self.module_repo.get_module_by_id(module_id=module_id)
            if not module:
                return BaseResponse.not_found(message=f"模块 ID {module_id} 不存在")

            # Clean up POINT type resources
            if module.type == ModuleType.POINT:
                # Clean up container if exists
                if module.container_id:
                    try:
                        await docker_service.stop_container(module.container_id)
                        logger.info(f"Stopped container: {module.container_id}")
                    except Exception as e:
                        logger.warning(f"Failed to stop container: {e}")

                # Clean up workspace directory
                if module.workspace_path:
                    try:
                        import shutil
                        workspace = Path(module.workspace_path)
                        if workspace.exists():
                            shutil.rmtree(workspace)
                            logger.info(f"Removed workspace: {module.workspace_path}")
                    except Exception as e:
                        logger.warning(f"Failed to remove workspace: {e}")

            # Delete module from database (cascades to children)
            await self.module_repo.delete_module(module_id=module_id)

            return BaseResponse.success(message="模块删除成功")
        except Exception as e:
            logger.error(f"删除模块失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"删除模块失败: {str(e)}")

    @log_print
    async def pull_module_code(self, module_id: int):
        """拉取 POINT 类型模块的最新代码"""
        try:
            module = await self.module_repo.get_module_by_id(module_id=module_id)
            if not module:
                return BaseResponse.not_found(message=f"模块 ID {module_id} 不存在")

            if module.type != ModuleType.POINT:
                return BaseResponse.error(message="只有 POINT 类型模块支持拉取代码")

            if not module.workspace_path:
                return BaseResponse.error(message="模块没有工作空间路径")

            # Get project info for git config
            project = await self.project_repo.get_project_by_id(project_id=module.project_id)
            if not project:
                return BaseResponse.error(message="关联的项目不存在")

            # Pull latest code
            from git import Repo

            workspace = Path(module.workspace_path)
            if not workspace.exists() or not (workspace / ".git").exists():
                return BaseResponse.error(message="工作空间不存在或不是Git仓库")

            repo = Repo(module.workspace_path)
            origin = repo.remotes.origin
            origin.pull()

            return BaseResponse.success(message="代码拉取成功")
        except Exception as e:
            logger.error(f"拉取代码失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"拉取代码失败: {str(e)}")

    @log_print
    async def restart_module_container(self, module_id: int):
        """重启 POINT 类型模块的容器"""
        try:
            module = await self.module_repo.get_module_by_id(module_id=module_id)
            if not module:
                return BaseResponse.not_found(message=f"模块 ID {module_id} 不存在")

            if module.type != ModuleType.POINT:
                return BaseResponse.error(message="只有 POINT 类型模块有容器")

            if not module.container_id:
                return BaseResponse.error(message="模块没有关联的容器")

            # Restart container
            await docker_service.restart_container(module.container_id)

            return BaseResponse.success(message="容器重启成功")
        except Exception as e:
            logger.error(f"重启容器失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"重启容器失败: {str(e)}")
