"""
Module Service

业务逻辑层 - Module operations with tree structure support
POINT type modules create sessions and manage workspaces
"""

import uuid
import logging
import json
import asyncio
from typing import Optional, AsyncGenerator
from pathlib import Path
from fastapi import Query

from app.api.chat_router import module_repo
from app.config.logging_config import log_print
from app.config import get_settings
from app.utils.model.response_model import BaseResponse, ListResponse
from app.db.repository import ModuleRepository, ProjectRepository, VersionRepository, SessionRepository, \
    MessageRepository
from app.db.schemas import ModuleCreate, ModuleUpdate, ModuleResponse, VersionCreate
from app.db.models.module import ModuleType
from app.core.executor import get_sandbox_executor
from app.core.github_service import GitHubService
from app.core.claude_service import SandboxService, session_manager
from app.utils.mysql_util import MySQLUtil
from datetime import datetime
from app.utils.prompt.prompt_build import generate_code_from_spec

logger = logging.getLogger(__name__)
settings = get_settings()
message_repo = MessageRepository()


class ModuleService:
    """
    模块服务类

    提供模块相关的所有业务逻辑操作，支持树形结构
    POINT 类型创建 session 和 workspace，拉取代码
    NODE 类型只做功能说明，URL 与子节点共享
    """

    def __init__(self):
        self.sort_code = 10000
        self.module_repo = ModuleRepository()
        self.project_repo = ProjectRepository()
        self.version_repo = VersionRepository()
        self.session_repo = SessionRepository()
        self.db = MySQLUtil(
      host="172.27.1.37",
      port=3306,
      user="root",
      password="123456",
      database="framework"
  )

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

            # # 创建 spec 目录
            # spec_dir = Path(workspace_path) / "spec"
            # spec_dir.mkdir(parents=True, exist_ok=True)

            # 构建提示词
#             prompt = f"""你是一位资深的软件架构师和技术文档专家。请根据以下功能需求，生成一份详细的技术规格文档（Technical Specification Document）。
#
# 功能需求：
# {require_content}
#
# 注意：
# - 文档应该足够详细，让AI能够根据文档直接生成代码
# - 使用Markdown格式
# - 代码示例使用代码块
# - 表格使用Markdown表格格式
# - 流程图使用Mermaid语法
#
# 请直接输出Markdown格式的文档内容，不要有任何额外的解释或说明。"""
#
#             # 获取沙箱服务实例
#             sandbox_service = await session_manager.get_service(
#                 session_id=session_id,
#                 workspace_path=workspace_path,
#             )
#
#             # 调用沙箱服务生成文档
#             logger.info("Calling sandbox service to generate spec document...")
#             messages = await sandbox_service.chat(prompt=prompt, session_id=session_id)
#
#             # 提取文本内容
#             spec_content = ""
#             for msg in messages:
#                 if msg.type == "text":
#                     spec_content += msg.content + "\n"
#
#             if not spec_content.strip():
#                 logger.error("Claude did not generate any content")
#                 return None
            return {"spec_content": require_content}

        except Exception as e:
            logger.error(f"Failed to generate spec document: {e}", exc_info=True)
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
            url_parent_id = module_data.pop("url_parent_id")

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
                        await service.create_branch(repo_path=workspace_path, branch_name= data.branch + '-' + session_id)
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
                        await self.module_repo.update_module(module_id=module_id, data=module_data)
                        if spec_dict["spec_content"]:
                            logger.info(f"Spec document generated successfully")

                            # 6. Generate code from spec and commit
                            logger.info(f"Generating code from spec for module: {module_id}")
                            commit_id, _ = await generate_code_from_spec(
                                spec_content=data.require_content,
                                workspace_path=workspace_path,
                                session_id=session_id,
                                module_code=data.code,
                                module_name=data.name,
                                module_url=data.url,
                                task_type="spec"
                            )

                            if commit_id:
                                logger.info(f"Code generated and committed successfully: {commit_id}")
                                module_data.update({
                                    "latest_commit_id": commit_id
                                })
                                await self.module_repo.update_module(module_id=module_id, data=module_data)

                                # 7. Savecommit to version table
                                try:
                                    # Generate version code based on timestamp
                                    version_code = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                                    version_data = VersionCreate(
                                        code=version_code,
                                        module_id=module_id,
                                        msg=f"{data.name} ({data.code}) 功能实现",
                                        commit=commit_id
                                    )
                                    version = await self.version_repo.create_version(
                                        data=version_data,
                                        created_by=created_by
                                    )
                                    logger.info(f"Version created: {version.id}, code: {version_code}")
                                except Exception as e:
                                    logger.error(f"Failed to create version record: {e}", exc_info=True)
                            else:
                                logger.warning("Code generation did not produce a commit")
                        else:
                            # await self.module_repo.delete_module(module_id=module_id)
                            return BaseResponse.error(message=f"创建模块失败: Spec document generation returned None")

                    except Exception as e:
                        logger.error(f"Failed in spec/code generation process: {e}", exc_info=True)
                        # await self.module_repo.delete_module(module_id=module_id)
                        return BaseResponse.error(message=f"创建模块失败: {str(e)}")
                        # Continue even if spec/code generation fails

                # 8. Refresh module data and add commit_id
                module = await self.module_repo.get_module_by_id(module_id=module_id)
                module.spec_file_path = spec_dict.get("spec_file_path")
                module.spec_content = spec_dict.get("spec_content")
                response_data = ModuleResponse.model_validate(module)

                # 创建沙箱容器 (optional, non-blocking)
                try:
                    executor = get_sandbox_executor()
                    container_info = await executor.create_workspace(
                        session_id=session_id,
                        workspace_path=workspace_path
                    )
                    logger.info(f"Sandbox container created: {container_info['id']}")
                    module_data.update({
                        "container_id": container_info["id"],
                    })
                    await self.module_repo.update_module(module_id=module_id, data=module_data)
                except Exception as e:
                    logger.warning(f"Failed to create container for module {module_id}: {e}")
                    # await self.module_repo.delete_module(module_id=module_id)
                    return BaseResponse.error(message=f"创建模块失败: {str(e)}")

                    # Continue even if container creation fails
                menu = {"full_name": module.name, "english_name": module.code, "url_address": module.url, "enable_mark": 1, "parent_id": url_parent_id, "sort_code": self.sort_code}
                insert_id = self.db.insert(table='sys_module', data=menu)
                module_data.update({
                    "url_id": insert_id,
                    "preview_url": settings.preview_ip + ':' + str(container_info["code_port"]) + data.url,
                })
                logger.info(f"preview_url: {settings.preview_ip + ':' + str(container_info['code_port']) + data.url}")
                await self.module_repo.update_module(module_id=module_id, data=module_data)
                return BaseResponse.success(
                    data=response_data,
                    message="POINT 模块创建成功，代码已拉取并生成"
                )

            else:
                # NODE type: simple creation without workspace
                menu = {"full_name": data.name, "english_name": data.code, "url_address": '/',
                        "enable_mark": 1, "sort_code": self.sort_code}
                insert_id = self.db.insert(table='sys_module', data=menu)
                module_data.update({
                    "url_id": insert_id,
                })
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
            # await self.module_repo.delete_module(module_id=module_id)
            # self.db.execute_update("DELETE FROM sys_module WHERE module_id=%s", module_id)
            return BaseResponse.error(message=f"创建模块失败: {str(e)}")

    async def create_module_stream(self, data: ModuleCreate, created_by: Optional[str] = None) -> AsyncGenerator[str, None]:
        """
        流式创建新模块（SSE）

        实时返回创建进度，适用于POINT类型模块的长时间操作

        生成的事件：
        - connected: 连接建立
        - step: {step: "step_name", status: "progress/success/error", message: "...", progress: 20}
        - complete: {module_id: xxx, session_id: xxx}
        - error: {message: "error message"}
        """
        module_id = None
        insert_id = None

        try:
            # 发送连接确认
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            await asyncio.sleep(0)

            # 步骤1: 验证项目
            yield f"data: {json.dumps({'type': 'step', 'step': 'validate_project', 'status': 'progress', 'message': '验证项目信息...', 'progress': 5})}\n\n"

            project = await self.project_repo.get_project_by_id(project_id=data.project_id)
            if not project:
                yield f"data: {json.dumps({'type': 'error', 'message': f'项目 ID {data.project_id} 不存在'})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'step', 'step': 'validate_project', 'status': 'success', 'message': '项目验证成功', 'progress': 10})}\n\n"

            # 步骤2: 检查模块代码唯一性
            yield f"data: {json.dumps({'type': 'step', 'step': 'check_code', 'status': 'progress', 'message': '检查模块代码唯一性...', 'progress': 15})}\n\n"

            existing = await self.module_repo.get_module_by_code(
                project_id=data.project_id,
                is_active=1,
                code=data.code
            )
            if existing:
                yield f"data: {json.dumps({'type': 'error', 'message': f'模块代码 {data.code} 在项目中已存在'})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'step', 'step': 'check_code', 'status': 'success', 'message': '模块代码检查通过', 'progress': 20})}\n\n"

            # 验证父节点
            if data.parent_id:
                parent = await self.module_repo.get_module_by_id(module_id=data.parent_id)
                if not parent or parent.project_id != data.project_id:
                    yield f"data: {json.dumps({'type': 'error', 'message': '父模块验证失败'})}\n\n"
                    return

            module_data = data.model_dump()
            url_parent_id = module_data.pop("url_parent_id")

            if data.type == ModuleType.POINT:
                # 步骤3: 生成session和workspace
                yield f"data: {json.dumps({'type': 'step', 'step': 'generate_session', 'status': 'progress', 'message': '生成会话和工作空间...', 'progress': 25})}\n\n"

                session_id = str(uuid.uuid4())
                workspace_path = str(settings.workspace_base_path / session_id)

                module_data.update({
                    "session_id": session_id,
                    "workspace_path": workspace_path,
                    "branch": data.branch or "main",
                    "is_active": 1,
                })

                yield f"data: {json.dumps({'type': 'step', 'step': 'generate_session', 'status': 'success', 'message': f'会话ID: {session_id}', 'progress': 30})}\n\n"

                # 步骤4: 克隆代码仓库
                if project.codebase:
                    yield f"data: {json.dumps({'type': 'step', 'step': 'clone_repo', 'status': 'progress', 'message': '正在克隆代码仓库...', 'progress': 35})}\n\n"

                    try:
                        service = GitHubService(token=project.token)
                        await service.clone_repo(
                            repo_url=project.codebase,
                            target_path=workspace_path,
                            branch=module_data.get("branch"),
                        )

                        yield f"data: {json.dumps({'type': 'step', 'step': 'clone_repo', 'status': 'success', 'message': '代码仓库克隆成功', 'progress': 45})}\n\n"

                        # 创建分支
                        yield f"data: {json.dumps({'type': 'step', 'step': 'create_branch', 'status': 'progress', 'message': '创建功能分支...', 'progress': 50})}\n\n"

                        await service.create_branch(repo_path=workspace_path, branch_name=data.branch + '-' + session_id)

                        yield f"data: {json.dumps({'type': 'step', 'step': 'create_branch', 'status': 'success', 'message': '功能分支创建成功', 'progress': 55})}\n\n"

                    except Exception as e:
                        yield f"data: {json.dumps({'type': 'error', 'message': f'代码拉取失败: {str(e)}'})}\n\n"
                        return

                # 步骤5: 创建沙箱容器
                yield f"data: {json.dumps({'type': 'step', 'step': 'create_container', 'status': 'progress', 'message': '创建沙箱容器...', 'progress': 60})}\n\n"

                try:
                    executor = get_sandbox_executor()
                    container_info = await executor.create_workspace(
                        session_id=session_id,
                        workspace_path=workspace_path
                    )
                    module_data.update({"container_id": container_info["id"]})
                    container_id_short = container_info["id"][:12]
                    yield f'data: {json.dumps({"type": "step", "step": "create_container", "status": "success", "message": f"容器ID: {container_id_short}", "preview_url": settings.preview_ip + ":" + str(container_info["code_port"]) + data.url, "progress": 65})}\n\n'
                except Exception as e:
                    logger.warning(f"Container creation failed: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'message': f'容器创建失败: {str(e)}'})}\n\n"
                    return

                # 步骤5: 创建数据库记录
                yield f"data: {json.dumps({'type': 'step', 'step': 'create_db_record', 'status': 'progress', 'message': '创建数据库记录...', 'progress': 70})}\n\n"

                module = await self.module_repo.create_module(data=module_data, created_by=created_by)
                await self.session_repo.create_session(
                    session_id=session_id,
                    name=project.code + '-' + data.code,
                    workspace_path=workspace_path,
                    github_repo_url=project.codebase,
                    github_branch=data.branch or "main",
                )
                module_id = module.id

                menu = {
                    "full_name": module.name,
                    "english_name": module.code,
                    "url_address": module.url,
                    "enable_mark": 1,
                    "parent_id": url_parent_id,
                    "sort_code": self.sort_code
                }
                insert_id = self.db.insert(table='sys_module', data=menu)
                module_data.update({
                    "url_id": insert_id,
                    "preview_url": settings.preview_ip + ':' + str(container_info["code_port"]) + data.url,
                })
                logger.info(f"preview_url: {settings.preview_ip + ':' + str(container_info['code_port']) + data.url}")
                await self.module_repo.update_module(module_id=module_id, data=module_data)

                yield f"data: {json.dumps({'type': 'step', 'step': 'create_db_record', 'status': 'success', 'message': f'模块ID: {module_id}', 'module_id': module_id, 'progress': 75})}\n\n"

                # 步骤6: 生成spec文档
                if data.require_content:
                    try:
                        await message_repo.create_message(
                            session_id=session_id,
                            role='user',
                            content=data.require_content,
                            tool_name=None,
                            tool_input=None,
                            tool_result=None,
                        )
                    except Exception as e:
                        logger.error(f"Failed to save messages: {e}", exc_info=True)

                    yield f"data: {json.dumps({'type': 'step', 'step': 'generate_spec', 'status': 'progress', 'message': '正在生成技术规格文档...', 'progress': 80})}\n\n"

                    message_queue = asyncio.Queue()
                    try:
                        task = asyncio.create_task(generate_code_from_spec(
                            spec_content=data.require_content,
                            workspace_path=workspace_path,
                            session_id=session_id,
                            module_code=data.code,
                            module_name=data.name,
                            module_url=data.url,
                            task_type="spec",
                            message_queue=message_queue,)
                        )
                        buffer = ""
                        while True:
                            chunk = await message_queue.get()
                            if chunk is None:
                                # 最后 flush 剩余内容（即使没有 \n）
                                if buffer:
                                    yield f"data: {json.dumps({'type': 'step', 'step': 'ai_think', 'status': 'success', 'message': 'ai思考...', 'ai_message': buffer, 'progress': 85}, ensure_ascii=False)}\n\n"
                                break
                            # 累加到缓冲区
                            buffer += chunk.content
                            # 持续检查缓冲区中是否有完整的行（以 \n 结尾）
                            while "\n\n" in buffer:
                                # 分割出第一个完整行（包含 \n）
                                line, buffer = buffer.split("\n\n", 1)
                                # 推送这一整行
                                yield f"data: {json.dumps({'type': 'step', 'step': 'ai_think', 'status': 'success', 'message': 'ai思考...', 'ai_message': line, 'progress': 85}, ensure_ascii=False)}\n\n"
                        spec_content, msg_list, result = await task
                        if spec_content:
                            yield f"data: {json.dumps({'type': 'step', 'step': 'generate_spec', 'status': 'success', 'message': 'Spec文档生成成功', 'spec_content': spec_content, 'progress': 85})}\n\n"
                            module_update = ModuleUpdate(spec_content=spec_content)
                            module_repo.update_module(module_id=module.session_id, module_update=module_update)
                        else:
                            yield f"data: {json.dumps({'type': 'step', 'step': 'generate_spec', 'status': 'error', 'message': 'Spec文档生成失败', 'spec_content': spec_content, 'progress': 85})}\n\n"
                        # 保存会话

                        try:
                            if msg_list:
                                await message_repo.create_message(
                                    session_id=session_id,
                                    role='assistant',
                                    content="".join(msg_list),
                                    tool_name=None,
                                    tool_input=None,
                                    tool_result=None,
                                )
                            if result:
                                await message_repo.create_message(
                                    session_id=session_id,
                                    role='assistant',
                                    content="".join(result),
                                    tool_name=None,
                                    tool_input=None,
                                    tool_result=None,
                                )
                        except Exception as e:
                            logger.error(f"Failed to save messages: {e}", exc_info=True)

                        yield f"data: {json.dumps({'type': 'step', 'step': 'generate_code', 'status': 'progress', 'message': '正在生成预览供您确认...', 'progress': 90})}\n\n"

                        yield f"data: {json.dumps({'type': 'step', 'step': 'generate_code', 'status': 'success', 'message': f'预览生成成功', 'progress': 100})}\n\n"

                    except Exception as e:
                        logger.error(f"Spec/Code generation failed: {e}", exc_info=True)
                        # await self.module_repo.delete_module(module_id=module_id)
                        yield f"data: {json.dumps({'type': 'error', 'message': f'文档/代码生成失败: {str(e)}'})}\n\n"
                        return

                # 完成
                module = await self.module_repo.get_module_by_id(module_id=module_id)
                response_data = ModuleResponse.model_validate(module)

                yield f"data: {json.dumps({'type': 'complete', 'module_id': module_id, 'session_id': session_id, 'data': response_data.model_dump(mode='json')})}\n\n"

            else:
                # NODE类型：简单创建
                yield f"data: {json.dumps({'type': 'step', 'step': 'create_node', 'status': 'progress', 'message': '创建NODE类型模块...', 'progress': 50})}\n\n"

                menu = {
                    "full_name": data.name,
                    "english_name": data.code,
                    "url_address": '/',
                    "enable_mark": 1,
                    "sort_code": self.sort_code
                }
                insert_id = self.db.insert(table='sys_module', data=menu)
                module_data.update({"url_id": insert_id})


                module = await self.module_repo.create_module(data=module_data, created_by=created_by)

                yield f"data: {json.dumps({'type': 'step', 'step': 'create_node', 'status': 'success', 'message': 'NODE模块创建成功', 'progress': 100})}\n\n"
                yield f"data: {json.dumps({'type': 'complete', 'module_id': module.id, 'data': ModuleResponse.model_validate(module).model_dump(mode='json')})}\n\n"

        except Exception as e:
            logger.error(f"Stream creation failed: {e}", exc_info=True)
            # if module_id:
            #     await self.module_repo.delete_module(module_id=module_id)
            # if insert_id:
            #     self.db.execute_update("DELETE FROM sys_module WHERE id=%s", insert_id)
            yield f"data: {json.dumps({'type': 'error', 'message': f'创建失败: {str(e)}'})}\n\n"

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
                if module.session_id:
                    try:
                        # executor = get_sandbox_executor()
                        # await executor.stop_container(module.session_id)
                        logger.info(f"Stopped container for session: {module.session_id}")
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
            self.db.execute_update("DELETE FROM sys_module WHERE id=%s", module.url_id)
            self.db.execute_update("DELETE FROM sys_module WHERE parent_id=%s", module.url_id)

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

            if not module.session_id:
                return BaseResponse.error(message="模块没有关联的会话")

            # Restart container
            # executor = get_sandbox_executor()
            # await executor.restart_container(
            #     session_id=module.session_id,
            #     workspace_path=module.workspace_path or ""
            # )

            return BaseResponse.success(message="容器重启成功")
        except Exception as e:
            logger.error(f"重启容器失败: {e}", exc_info=True)
            return BaseResponse.error(message=f"重启容器失败: {str(e)}")

    async def optimize_module_stream(
        self,
        session_id: str,
        content: str,
        updated_by: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式优化已创建的POINT类型模块（SSE）

        根据用户新的需求对现有代码进行优化，实时返回优化进度

        流程：
        1. 查找并验证模块
        2. 加载历史会话上下文
        3. 读取工作空间代码
        4. 结合所有上下文更新spec_content
        5. 生成优化后的代码
        6. 创建commit和version
        7. 重启容器

        生成的事件：
        - connected: 连接建立
        - step: {step, status, message, progress}
        - complete: {module_id, commit_id, version_id}
        - error: {message}
        """
        try:
            # 发送连接确认
            yield f"data: {json.dumps({'type': 'connected', 'message': '开始优化模块'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)

            # 步骤1: 查找模块
            yield f"data: {json.dumps({'type': 'step', 'step': 'find_module', 'status': 'progress', 'message': '查找模块...', 'progress': 5}, ensure_ascii=False)}\n\n"

            module = await self.module_repo.get_module_by_session_id(session_id=session_id)
            if not module:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Session ID {session_id} 对应的模块不存在'}, ensure_ascii=False)}\n\n"
                return

            if module.type != ModuleType.POINT:
                yield f"data: {json.dumps({'type': 'error', 'message': '只能优化POINT类型模块'}, ensure_ascii=False)}\n\n"
                return

            yield f"data: {json.dumps({'type': 'step', 'step': 'find_module', 'status': 'success', 'message': f'找到模块: {module.name}', 'progress': 10}, ensure_ascii=False)}\n\n"

            # 步骤2: 验证工作空间
            yield f"data: {json.dumps({'type': 'step', 'step': 'verify_workspace', 'status': 'progress', 'message': '验证工作空间...', 'progress': 15}, ensure_ascii=False)}\n\n"

            workspace_path = module.workspace_path
            if not workspace_path or not Path(workspace_path).exists():
                yield f"data: {json.dumps({'type': 'error', 'message': '工作空间不存在'}, ensure_ascii=False)}\n\n"
                return

            yield f"data: {json.dumps({'type': 'step', 'step': 'verify_workspace', 'status': 'success', 'message': '工作空间验证成功', 'progress': 20}, ensure_ascii=False)}\n\n"

            await message_repo.create_message(
                session_id=session_id,
                role='user',
                content=content,
                tool_name=None,
                tool_input=None,
                tool_result=None,
            )

            # 步骤5: 生成更新后的spec文档
            yield f"data: {json.dumps({'type': 'step', 'step': 'update_spec', 'status': 'progress', 'message': '根据优化需求更新spec文档...', 'progress': 45}, ensure_ascii=False)}\n\n"


            message_queue = asyncio.Queue()
            try:
                task = asyncio.create_task(generate_code_from_spec(
                    spec_content=module.require_content,
                    workspace_path=workspace_path,
                    session_id=session_id,
                    module_code=module.code,
                    module_name=module.name,
                    module_url=module.url,
                    task_type="",
                    message_queue=message_queue, )
                )
                buffer = ""
                while True:
                    chunk = await message_queue.get()
                    if chunk is None:
                        # 最后 flush 剩余内容（即使没有 \n）
                        if buffer:
                            yield f"data: {json.dumps({'type': 'step', 'step': 'ai_think', 'status': 'success', 'message': 'ai思考...', 'ai_message': buffer, 'progress': 50}, ensure_ascii=False)}\n\n"
                        break
                    # 累加到缓冲区
                    buffer += chunk.content
                    # 持续检查缓冲区中是否有完整的行（以 \n 结尾）
                    while "\n\n" in buffer:
                        # 分割出第一个完整行（包含 \n）
                        line, buffer = buffer.split("\n\n", 1)
                        # 推送这一整行
                        yield f"data: {json.dumps({'type': 'step', 'step': 'ai_think', 'status': 'success', 'message': 'ai思考...', 'ai_message': line, 'progress': 60}, ensure_ascii=False)}\n\n"
                spec_content, msg_list, result = await task
                if spec_content:
                    yield f"data: {json.dumps({'type': 'step', 'step': 'update_spec', 'status': 'success', 'message': 'spec更新成功', 'spec_content': spec_content, 'progress': 80}, ensure_ascii=False)}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'spec更新失败', 'spec_content': spec_content, 'progress': 100}, ensure_ascii=False)}\n\n"
                    return
                # 保存会话
                try:
                    if msg_list:
                        await message_repo.create_message(
                            session_id=session_id,
                            role='assistant',
                            content="".join(msg_list),
                            tool_name=None,
                            tool_input=None,
                            tool_result=None,
                        )
                    if result:
                        await message_repo.create_message(
                            session_id=session_id,
                            role='assistant',
                            content="".join(result),
                            tool_name=None,
                            tool_input=None,
                            tool_result=None,
                        )
                except Exception as e:
                    logger.error(f"Failed to save messages: {e}", exc_info=True)
                module_update = ModuleUpdate(spec_content=spec_content)
                module_repo.update_module(module_id=module.session_id, module_update=module_update)

            except Exception as e:
                logger.error(f"Failed to generate code: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'message': f'代码生成失败: {str(e)}'}, ensure_ascii=False)}\n\n"
                return

            # 完成
            yield f"data: {json.dumps({'type': 'complete', 'module_id': module.id, 'spec_content': spec_content, 'version_id': '', 'message': '优化完成', 'progress': 100}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"Optimization stream failed: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': f'优化失败: {str(e)}'}, ensure_ascii=False)}\n\n"

    async def build_module_stream(
            self,
            session_id: str,
            content: str,
            updated_by: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        try:
            # 发送连接确认
            yield f"data: {json.dumps({'type': 'connected', 'message': '开始生成代码'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)

            # 步骤1: 查找模块
            yield f"data: {json.dumps({'type': 'step', 'step': 'find_module', 'status': 'progress', 'message': '查找模块...', 'progress': 5}, ensure_ascii=False)}\n\n"

            module = await self.module_repo.get_module_by_session_id(session_id=session_id)
            if not module:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Session ID {session_id} 对应的模块不存在'}, ensure_ascii=False)}\n\n"
                return

            if module.type != ModuleType.POINT:
                yield f"data: {json.dumps({'type': 'error', 'message': '只能优化POINT类型模块'}, ensure_ascii=False)}\n\n"
                return

            yield f"data: {json.dumps({'type': 'step', 'step': 'find_module', 'status': 'success', 'message': f'找到模块: {module.name}', 'progress': 10}, ensure_ascii=False)}\n\n"

            # 步骤2: 验证工作空间
            yield f"data: {json.dumps({'type': 'step', 'step': 'verify_workspace', 'status': 'progress', 'message': '验证工作空间...', 'progress': 15}, ensure_ascii=False)}\n\n"

            workspace_path = module.workspace_path
            if not workspace_path or not Path(workspace_path).exists():
                yield f"data: {json.dumps({'type': 'error', 'message': '工作空间不存在'}, ensure_ascii=False)}\n\n"
                return

            yield f"data: {json.dumps({'type': 'step', 'step': 'verify_workspace', 'status': 'success', 'message': '工作空间验证成功', 'progress': 20}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'type': 'step', 'step': 'code_build', 'status': 'success', 'message': '开始生成代码', 'progress': 30}, ensure_ascii=False)}\n\n"
            # 步骤3: 生成代码
            message_queue = asyncio.Queue()
            try:
                task = asyncio.create_task(generate_code_from_spec(
                    spec_content=module.require_content,
                    workspace_path=workspace_path,
                    session_id=session_id,
                    module_code=module.code,
                    module_name=module.name,
                    module_url=module.url,
                    task_type="build",
                    message_queue=message_queue, )
                )
                buffer = ""
                while True:
                    chunk = await message_queue.get()
                    if chunk is None:
                        # 最后 flush 剩余内容（即使没有 \n）
                        if buffer:
                            yield f"data: {json.dumps({'type': 'step', 'step': 'ai_think', 'status': 'success', 'message': 'ai思考...', 'ai_message': buffer, 'progress': 50}, ensure_ascii=False)}\n\n"
                        break
                    # 累加到缓冲区
                    buffer += chunk.content
                    # 持续检查缓冲区中是否有完整的行（以 \n 结尾）
                    while "\n\n" in buffer:
                        # 分割出第一个完整行（包含 \n）
                        line, buffer = buffer.split("\n\n", 1)
                        # 推送这一整行
                        yield f"data: {json.dumps({'type': 'step', 'step': 'ai_think', 'status': 'success', 'message': 'ai思考...', 'ai_message': line, 'progress': 60}, ensure_ascii=False)}\n\n"
                spec_content, msg_list, result = await task
                # 保存会话
                try:
                    if msg_list:
                        await message_repo.create_message(
                            session_id=session_id,
                            role='assistant',
                            content="".join(msg_list),
                            tool_name=None,
                            tool_input=None,
                            tool_result=None,
                        )
                    if result:
                        await message_repo.create_message(
                            session_id=session_id,
                            role='assistant',
                            content="".join(result),
                            tool_name=None,
                            tool_input=None,
                            tool_result=None,
                        )
                except Exception as e:
                    logger.error(f"Failed to save messages: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'step', 'step': 'code_build', 'status': 'success', 'message': '代码生成成功', 'progress': 45}, ensure_ascii=False)}\n\n"

            except Exception as e:
                logger.error(f"Failed to generate code: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'message': f'代码生成失败: {str(e)}'}, ensure_ascii=False)}\n\n"
                return

            # 步骤4: 创建版本记录
            yield f"data: {json.dumps({'type': 'step', 'step': 'create_version', 'status': 'progress', 'message': '创建版本记录...', 'progress': 50}, ensure_ascii=False)}\n\n"
            # 使用 GitHubService 进行本地 commit
            commit_id = None
            try:
                yield f"data: {json.dumps({'type': 'step', 'step': 'commit', 'status': 'success', 'message': f'代码进行commit', 'progress': 55}, ensure_ascii=False)}\n\n"
                # Commit message
                commit_message = f"[SpecCoding Auto Commit] - {module.name} ({module.code}) 功能实现"

                # 执行commit
                from git import Repo
                repo = Repo(workspace_path)

                # Add all changes
                repo.git.add(A=True)
                # Check if there are staged changes to commit
                staged_files = repo.git.diff("--cached", "--name-only")

                # Check if there are changes to commit
                if staged_files.strip():
                    # Commit
                    commit = repo.index.commit(commit_message)
                    commit_id = commit.hexsha[:12]  # 使用前12位
                    repo.git.push()

                    logger.info(f"Code committed successfully: {commit_id}")
                    yield f"data: {json.dumps({'type': 'step', 'step': 'commit', 'status': 'success', 'message': f'commit完成,id: {commit_id}', 'progress': 60}, ensure_ascii=False)}\n\n"
                else:
                    logger.warning("No changes to commit")
                    yield f"data: {json.dumps({'type': 'step', 'step': 'commit', 'status': 'skipped', 'message': '无变更，跳过提交', 'progress': 60}, ensure_ascii=False)}\n\n"
                    return

            except Exception as e:
                logger.error(f"Failed to commit code: {e}", exc_info=True)
                return


            version_id = None
            try:
                version_code = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                version_data = VersionCreate(
                    code=version_code,
                    module_id=module.id,
                    msg=f"{module.name} 代码优化: {content[:100]}",
                    commit=commit_id
                )
                version = await self.version_repo.create_version(
                    data=version_data,
                    created_by=updated_by
                )
                version_id = version.id

                yield f"data: {json.dumps({'type': 'step', 'step': 'create_version', 'status': 'success', 'message': f'版本创建成功: {version_code}', 'progress': 80}, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error(f"Failed to create version: {e}")
                yield f"data: {json.dumps({'type': 'step', 'step': 'create_version', 'status': 'warning', 'message': '版本创建失败', 'progress': 80}, ensure_ascii=False)}\n\n"

            # 步骤5: 更新模块的latest_commit_id
            yield f"data: {json.dumps({'type': 'step', 'step': 'update_module', 'status': 'progress', 'message': '更新模块信息...', 'progress': 90}, ensure_ascii=False)}\n\n"

            try:
                module_update = ModuleUpdate(latest_commit_id=commit_id, spec_content=spec_content)
                await self.module_repo.update_module(
                    module_id=module.id,
                    data=module_update
                )
                yield f"data: {json.dumps({'type': 'step', 'step': 'update_module', 'status': 'success', 'message': '模块信息更新成功', 'progress': 100}, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error(f"Failed to update module: {e}")
                yield f"data: {json.dumps({'type': 'step', 'step': 'update_module', 'status': 'warning', 'message': '模块更新失败', 'progress': 100}, ensure_ascii=False)}\n\n"

            # 完成
            yield f"data: {json.dumps({'type': 'complete', 'module_id': module.id, 'spec_content': spec_content, 'version_id': version_id, 'message': '代码构建完成'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"Optimization stream failed: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': f'优化失败: {str(e)}'}, ensure_ascii=False)}\n\n"


