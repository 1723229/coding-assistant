"""
Module Service

业务逻辑层 - Module operations with tree structure support
POINT type modules create sessions and manage workspaces
"""

import uuid
import logging
import aiofiles
from typing import Optional
from pathlib import Path
from fastapi import Query

from app.config.logging_config import log_print
from app.config import get_settings
from app.utils.model.response_model import BaseResponse, ListResponse
from app.db.repository import ModuleRepository, ProjectRepository, VersionRepository, SessionRepository
from app.db.schemas import ModuleCreate, ModuleUpdate, ModuleResponse, VersionCreate
from app.db.models.module import ModuleType
from app.core.docker_service import docker_service
from app.core.github_service import GitHubService
from app.core.claude_service import ClaudeService, MessageType
from datetime import datetime

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
        self.version_repo = VersionRepository()
        self.session_repo = SessionRepository()

    async def _generate_spec_document(
        self,
        require_content: str,
        module_name: str,
        module_code: str,
        workspace_path: str,
        session_id: str
    ) -> Optional[dict]:
        """
        使用 Claude 生成技术规格文档

        Args:
            require_content: 功能需求描述
            module_name: 模块名称
            module_code: 模块代码
            workspace_path: 工作空间路径
            session_id: 会话ID

        Returns:
            生成的规格文档路径，失败返回 None
        """
        try:
            logger.info(f"Generating spec document for module: {module_code}")

            # 创建 spec 目录
            spec_dir = Path(workspace_path) / "spec"
            spec_dir.mkdir(parents=True, exist_ok=True)

            # 构建提示词
            prompt = f"""你是一位资深的软件架构师和技术文档专家。请根据以下功能需求，生成一份详细的技术规格文档（Technical Specification Document）。

功能需求：
{require_content}

注意：
- 文档应该足够详细，让AI能够根据文档直接生成代码
- 使用Markdown格式
- 代码示例使用代码块
- 表格使用Markdown表格格式
- 流程图使用Mermaid语法

请直接输出Markdown格式的文档内容，不要有任何额外的解释或说明。"""

            # 创建 ClaudeService 实例
            claude_service = ClaudeService(
                workspace_path=workspace_path,
                session_id=session_id,
                permission_mode="bypassPermissions"  # 使用自动批准模式
            )

            # 调用 Claude 生成文档
            logger.info("Calling Claude to generate spec document...")
            messages = await claude_service.chat(prompt=prompt, session_id=session_id)

            # 提取文本内容
            spec_content = ""
            for msg in messages:
                if msg.type == "text":
                    spec_content += msg.content + "\n"

            if not spec_content.strip():
                logger.error("Claude did not generate any content")
                return None

            # print("Generated spec document:", spec_content)
            # 保存到文件
            spec_file_path = spec_dir / f"{module_code}_spec.md"
            async with aiofiles.open(spec_file_path, "w", encoding="utf-8") as f:
                await f.write(spec_content)

            logger.info(f"Spec document saved to: {spec_file_path}")
            return {"spec_file_path": spec_file_path, "spec_content": spec_content}

        except Exception as e:
            logger.error(f"Failed to generate spec document: {e}", exc_info=True)
            return None

    async def _generate_code_from_spec(
        self,
        spec_file_path: str,
        workspace_path: str,
        session_id: str,
        module_name: str,
        module_code: str
    ) -> Optional[str]:
        """
        使用 Claude 根据规格文档生成代码并commit

        Args:
            spec_file_path: 规格文档路径
            workspace_path: 工作空间路径
            session_id: 会话ID
            module_name: 模块名称
            module_code: 模块代码

        Returns:
            commit_id，失败返回 None
        """
        try:
            logger.info(f"Generating code from spec for module: {module_code}")

            # 读取spec文档内容
            async with aiofiles.open(spec_file_path, "r", encoding="utf-8") as f:
                spec_content = await f.read()

            # 构建提示词
            prompt = f"""你是一位资深的全栈开发工程师。我已经为你准备了一份详细的技术规格文档，请根据这份文档和代码，生成完整的代码实现。

模块信息：
- 模块名称：{module_name}
- 模块代码：{module_code}

技术规格文档内容：
{spec_content}

请根据上述技术规格文档，完成以下任务：

1. **仔细阅读工作空间中的现有代码**：使用Read工具查看当前项目结构和代码
2. **分析技术栈**：了解项目使用的技术栈、框架和编码规范
3. **生成代码**：根据规格文档，使用Write和Edit工具生成或修改代码文件
4. **确保代码质量**：
   - 遵循项目现有的代码风格和规范
   - 添加必要的注释和文档
   - 确保代码的可读性和可维护性
   - 处理错误和边界情况
5. **完整实现**：确保所有规格文档中描述的功能都已实现

注意事项：
- 不要只是生成示例代码，而是要生成可以直接运行的完整代码
- 使用项目现有的目录结构和命名规范
- 如果需要安装新的依赖，请更新相应的依赖配置文件
- 生成的代码应该与现有代码无缝集成

请开始实现代码，使用工具直接修改工作空间中的文件。"""

            # 创建 ClaudeService 实例
            claude_service = ClaudeService(
                workspace_path=workspace_path,
                session_id=session_id,
                permission_mode="bypassPermissions"  # 使用自动批准模式
            )

            # 调用 Claude 生成代码（使用streaming）
            logger.info("Calling Claude to generate code from spec...")

            # 收集所有消息用于日志
            all_messages = []
            async for msg in claude_service.chat_stream(prompt=prompt, session_id=session_id):
                all_messages.append(msg)
                # 记录重要的消息类型
                if msg.type in [MessageType.TOOL_USE.value, MessageType.ERROR.value]:
                    logger.info(f"Claude message: {msg.type} - {msg.content[:200]}")

            # 检查是否成功
            has_error = any(msg.type == MessageType.ERROR.value for msg in all_messages)
            if has_error:
                logger.error("Claude encountered errors during code generation")
                return None

            logger.info("Code generation completed, now committing changes...")

            # 使用 GitHubService 进行本地 commit
            try:
                github_service = GitHubService()

                # Commit message
                commit_message = f"[SpecCoding Auto Commit] - {module_name} ({module_code}) 功能实现"

                # 执行commit
                from git import Repo
                repo = Repo(workspace_path)

                # Add all changes
                repo.git.add(A=True)

                # Check if there are changes to commit
                if repo.is_dirty() or repo.untracked_files:
                    # Commit
                    commit = repo.index.commit(commit_message)
                    commit_id = commit.hexsha[:12]  # 使用前12位

                    logger.info(f"Code committed successfully: {commit_id}")
                    return commit_id
                else:
                    logger.warning("No changes to commit")
                    return None

            except Exception as e:
                logger.error(f"Failed to commit code: {e}", exc_info=True)
                return None

        except Exception as e:
            logger.error(f"Failed to generate code from spec: {e}", exc_info=True)
            return None

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
                is_active = 1,
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


                # 2. Clone GitHub repository
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
                        await service.create_branch(repo_path=workspace_path, branch_name= project.code + '-' + data.code, session_id=session_id)
                        logger.info(f"Branch created successfully to: {workspace_path}")
                    except Exception as e:
                        # Mark module as inactive if clone fails
                        return BaseResponse.error(
                            message=f"代码拉取失败: {str(e)}"
                        )

                # 3. Create module in database first
                module = await self.module_repo.create_module(
                    data=module_data,
                    created_by=created_by
                )
                await self.session_repo.create_session(
                    session_id=session_id,
                    name=project.code + '-' + data.code,
                    workspace_path=workspace_path,
                    github_repo_url=project.codebase,
                    github_branch=data.branch or "main",
                )
                module_id = module.id
                logger.info(f"Module created in database: {module_id}")

                # 5. Generate spec document if require_content is provided
                commit_id = None

                if data.require_content:
                    try:
                        logger.info(f"Generating spec document for module: {module_id}")
                        spec_dict = await self._generate_spec_document(
                            require_content=data.require_content,
                            module_name=data.name,
                            module_code=data.code,
                            workspace_path=workspace_path,
                            session_id=session_id
                        )
                        module_data.update({
                            "spec_file_path": spec_dict["spec_file_path"],
                        })
                        await self.module_repo.update_module(module_id=module_id, data=module_data)
                        # if spec_dict["spec_file_path"]:
                        #     logger.info(f"Spec document generated successfully: {spec_dict["spec_file_path"]}")
                        #
                        #     # 6. Generate code from spec and commit
                        #     logger.info(f"Generating code from spec for module: {module_id}")
                        #     commit_id = await self._generate_code_from_spec(
                        #         spec_file_path=spec_file_path,
                        #         workspace_path=workspace_path,
                        #         session_id=session_id,
                        #         module_name=data.name,
                        #         module_code=data.code
                        #     )
                        #
                        #     if commit_id:
                        #         logger.info(f"Code generated and committed successfully: {commit_id}")
                        #
                        #         # 7. Save commit to version table
                        #         try:
                        #             # Generate version code based on timestamp
                        #             version_code = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        #             version_data = VersionCreate(
                        #                 code=version_code,
                        #                 module_id=module_id,
                        #                 msg=f"{data.name} ({data.code}) 功能实现",
                        #                 commit=commit_id
                        #             )
                        #             version = await self.version_repo.create_version(
                        #                 data=version_data,
                        #                 created_by=created_by
                        #             )
                        #             logger.info(f"Version created: {version.id}, code: {version_code}")
                        #         except Exception as e:
                        #             logger.error(f"Failed to create version record: {e}", exc_info=True)
                        #     else:
                        #         logger.warning("Code generation did not produce a commit")
                        # else:
                        #     logger.warning("Spec document generation returned None")
                    except Exception as e:
                        logger.error(f"Failed in spec/code generation process: {e}", exc_info=True)
                        await self.module_repo.delete_module(module_id=module_id)
                        return BaseResponse.error(message=f"创建模块失败: {str(e)}")
                        # Continue even if spec/code generation fails

                # 8. Refresh module data and add commit_id
                module = await self.module_repo.get_module_by_id(module_id=module_id)
                module.spec_file_path = spec_dict.get("spec_file_path")
                module.spec_content = spec_dict.get("spec_content")
                response_data = ModuleResponse.model_validate(module)

                # Add latest_commit_id to response
                if commit_id:
                    response_data.latest_commit_id = commit_id

                # todo Create Docker container (optional, non-blocking)
                try:
                    container_info = await docker_service.create_workspace(
                        session_id=session_id,
                        workspace_path=workspace_path
                    )
                    logger.info(f"Docker container created: {container_info.id}")
                    module_data.update({
                        "container_id": container_info.id,
                    })
                    await self.module_repo.update_module(module_id=module_id, data=module_data)
                except Exception as e:
                    logger.warning(f"Failed to create container for module {module_id}: {e}")
                    await self.module_repo.delete_module(module_id=module_id)
                    return BaseResponse.error(message=f"创建模块失败: {str(e)}")

                    # Continue even if container creation fails

                return BaseResponse.success(
                    data=response_data,
                    message="POINT 模块创建成功，代码已拉取并生成"
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
                    is_active = 1,
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
