"""
Chat API Router

聊天相关的API路由定义
使用SSE (Server-Sent Events) 进行流式聊天，HTTP用于历史记录和统计
"""

import asyncio
import json
import logging
from typing import Optional, Dict, AsyncGenerator
from pathlib import Path as _Path
from datetime import datetime

from app.config import get_settings
from app.core.claude_service import ClaudeService, ChatMessage, session_claude_manager, MessageType
from app.core.github_service import GitHubService
from app.db.repository import SessionRepository, MessageRepository, ModuleRepository, VersionRepository
from app.db.schemas.version import VersionCreate
from app.service.chat_service import ChatService
from fastapi import APIRouter, Query, Body, Path
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# 创建路由器
chat_router = APIRouter(prefix="/chat", tags=["chat"])

settings = get_settings()
logger = logging.getLogger(__name__)

# Repository和Service实例
session_repo = SessionRepository()
message_repo = MessageRepository()
module_repo = ModuleRepository()
version_repo = VersionRepository()
chat_service = ChatService()


# ===================
# Request Models
# ===================

class ChatRequest(BaseModel):
    """聊天请求模型"""
    content: str


class SpecGenerationRequest(BaseModel):
    """Spec文档生成请求模型"""
    content: str = Field(..., description="功能需求描述")


# ===================
# Active Sessions Tracking
# ===================

class SessionManager:
    """会话管理器 - 跟踪活跃的流式会话"""

    def __init__(self):
        self.active_sessions: Dict[str, bool] = {}

    def start_session(self, session_id: str):
        """开始会话"""
        self.active_sessions[session_id] = True
        logger.info(f"Session started: {session_id}")

    def stop_session(self, session_id: str):
        """停止会话"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id] = False
            logger.info(f"Session stopped: {session_id}")

    def is_active(self, session_id: str) -> bool:
        """检查会话是否活跃"""
        return self.active_sessions.get(session_id, False)


session_manager = SessionManager()


# ===================
# Helper Functions
# ===================


def chat_message_to_dict(msg: ChatMessage) -> dict:
    """将ChatMessage转换为dict"""
    return msg.to_dict()


async def save_message(
        session_id: str,
        role: str,
        content: str,
        tool_name: Optional[str] = None,
        tool_input: Optional[str] = None,
        tool_result: Optional[str] = None,
):
    """保存消息到数据库"""
    await message_repo.create_message(
        session_id=session_id,
        role=role,
        content=content,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_result=tool_result,
    )


# ===================
# SSE Stream Route
# ===================

async def chat_stream_generator(
        session_id: str,
        user_message: str,
        workspace_path: str,
) -> AsyncGenerator[str, None]:
    """
    SSE流式生成器

    发送格式: data: {json}\n\n
    """
    try:
        # 标记会话为活跃
        session_manager.start_session(session_id)

        # 立即发送连接确认 - 确保客户端知道连接已建立
        yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"

        # 强制刷新
        await asyncio.sleep(0)

        # 保存用户消息
        await save_message(session_id, "user", user_message)

        # 创建Claude服务
        claude_service = await session_claude_manager.get_service(
            session_id=session_id,
            workspace_path=workspace_path,
        )

        # 流式响应
        full_response = []
        try:
            async for chat_msg in claude_service.chat_stream(
                    user_message,
                    session_id=session_id,
            ):
                # 检查会话是否被中断
                if not session_manager.is_active(session_id):
                    yield f"data: {json.dumps({'type': 'interrupted', 'message': 'Stream interrupted'})}\n\n"
                    break

                msg_dict = chat_message_to_dict(chat_msg)
                yield f"data: {json.dumps(msg_dict)}\n\n"

                # 收集文本用于保存
                if chat_msg.type in ("text", "text_delta"):
                    full_response.append(chat_msg.content)

                # 小延迟防止刷屏
                await asyncio.sleep(0.01)

            # 保存助手响应
            if full_response:
                await save_message(
                    session_id,
                    "assistant",
                    "".join(full_response),
                )

            # 发送完成信号
            yield f"data: {json.dumps({'type': 'response_complete'})}\n\n"

        except Exception as e:
            logger.error(f"[SSE] Error during chat: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    finally:
        # 标记会话为非活跃
        session_manager.stop_session(session_id)


@chat_router.post(
    "/stream/{session_id}",
    summary="SSE流式聊天",
    operation_id="chat_stream"
)
async def chat_stream(
        session_id: str = Path(description="Session ID"),
        request: ChatRequest = Body(...),
):
    """
    SSE流式聊天端点

    使用Server-Sent Events进行流式响应
    客户端应使用EventSource连接到此端点
    """
    # 获取会话信息
    try:
        session = await session_repo.get_session_by_id(session_id)

        if not session:
            return {"error": "Session not found"}

        workspace_path = session.workspace_path
        logger.info(f"[SSE] Starting chat for session: {session.name}")

    except Exception as e:
        logger.error(f"[SSE] Database error: {e}")
        return {"error": f"Database error: {str(e)}"}

    # 返回SSE流
    return StreamingResponse(
        chat_stream_generator(session_id, request.content, workspace_path),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用nginx缓冲
        }
    )


@chat_router.post(
    "/interrupt/{session_id}",
    summary="中断聊天流",
    operation_id="interrupt_chat"
)
async def interrupt_chat(session_id: str = Path(..., description="Session ID")):
    """中断当前的流式响应"""
    try:
        session_manager.stop_session(session_id)

        # 也尝试中断Claude服务
        claude_service = await session_claude_manager.get_service(
            session_id=session_id,
            workspace_path="",  # 中断时不需要workspace_path
        )
        await claude_service.interrupt()

        return {"message": "Chat stream interrupted", "session_id": session_id}
    except Exception as e:
        logger.error(f"Failed to interrupt chat: {e}")
        return {"error": str(e)}


# ===================
# HTTP Routes
# ===================

@chat_router.get(
    "/history/{session_id}",
    summary="获取聊天历史",
    operation_id="get_chat_history"
)
async def get_chat_history(
        session_id: str,
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, le=500, description="Maximum number of records"),
):
    """获取会话的聊天历史"""
    return await chat_service.get_chat_history(session_id, skip=skip, limit=limit)


@chat_router.get(
    "/stats/{session_id}",
    summary="获取会话统计",
    operation_id="get_session_stats"
)
async def get_session_stats(session_id: str):
    """获取会话统计信息"""
    return await chat_service.get_session_stats(session_id)


@chat_router.get(
    "/stats",
    summary="获取全部统计",
    operation_id="get_all_stats"
)
async def get_all_stats():
    """获取所有会话的统计信息"""
    return await chat_service.get_all_stats()

async def chat_stream_with_auto_commit_generator(
        session_id: str,
        user_message: str,
        workspace_path: str,
) -> AsyncGenerator[str, None]:
    """
    带自动commit功能的SSE流式生成器

    流程：
    1. 获取对话前的workspace状态
    2. 执行Claude对话
    3. 检测workspace是否有变更
    4. 如果有变更，自动commit
    5. 根据session_id查找module
    6. 创建新的version记录
    7. 更新module的latest_commit_id

    发送格式: data: {json}\n\n
    """
    try:
        # 标记会话为活跃
        session_manager.start_session(session_id)

        # 立即发送连接确认
        yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
        await asyncio.sleep(0)

        # 保存用户消息
        await save_message(session_id, "user", user_message)

        # 创建GitHub服务实例
        github_service = GitHubService()

        # 记录对话前的Git状态（获取当前HEAD commit）
        initial_commit_sha = None
        has_workspace = workspace_path and _Path(workspace_path).exists()

        if has_workspace:
            try:
                from git import Repo
                repo = Repo(workspace_path)
                initial_commit_sha = repo.head.commit.hexsha if repo.head.is_valid() else None
            except Exception as e:
                logger.warning(f"Failed to get initial commit: {e}")

        # 构建提示词
        prompt = f"""你是一位资深的全栈开发工程师。我已经为你准备了一份详细的技术规格文档，请根据这份文档和代码，生成完整的代码实现。

仓库信息：{repo}

技术规格文档内容：
{user_message}

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

        # 创建Claude服务
        claude_service = await session_claude_manager.get_service(
            session_id=session_id,
            workspace_path=workspace_path,
        )

        # 流式响应
        full_response = []
        try:
            async for chat_msg in claude_service.chat_stream(
                    prompt=prompt,
                    session_id=session_id,
            ):
                # 检查会话是否被中断
                if not session_manager.is_active(session_id):
                    yield f"data: {json.dumps({'type': 'interrupted', 'message': 'Stream interrupted'})}\n\n"
                    break

                msg_dict = chat_message_to_dict(chat_msg)
                yield f"data: {json.dumps(msg_dict)}\n\n"

                # 收集文本用于保存
                if chat_msg.type in ("text", "text_delta"):
                    full_response.append(chat_msg.content)

                # 小延迟防止刷屏
                await asyncio.sleep(0.01)

            # 保存助手响应
            if full_response:
                await save_message(
                    session_id,
                    "assistant",
                    "".join(full_response),
                )

            # 对话完成后检查是否有代码变更，如果有则自动commit
            if has_workspace:
                try:
                    # 检查是否有本地变更
                    changes = await github_service.get_local_changes(
                        repo_path=workspace_path,
                        include_diff=False
                    )

                    if changes:
                        logger.info(f"[Auto Commit] Detected {len(changes)} changes in workspace")

                        # 发送提示信息
                        yield f"data: {json.dumps({'type': 'info', 'content': f'Detected {len(changes)} file changes, auto-committing...'})}\n\n"

                        # 生成commit message
                        changed_files = [c.path for c in changes]
                        commit_msg = f"[SpecCoding Auto Commit] - Updated {len(changes)} files: {', '.join(changed_files[:5])}"
                        if len(changed_files) > 5:
                            commit_msg += f" and {len(changed_files) - 5} more"

                        # 执行commit
                        commit_sha = await github_service.commit_changes(
                            repo_path=workspace_path,
                            message=commit_msg,
                            files=None  # commit所有变更
                        )

                        logger.info(f"[Auto Commit] Created commit: {commit_sha}")
                        yield f"data: {json.dumps({'type': 'commit', 'commit_sha': commit_sha, 'message': commit_msg})}\n\n"

                        # 根据session_id查找module
                        module = await module_repo.get_module_by_session_id(session_id=session_id)

                        if module:
                            logger.info(f"[Auto Commit] Found module: {module.id} (code: {module.code})")

                            # 获取最新版本号，生成新版本号
                            latest_version = await version_repo.get_latest_version(module_id=module.id)
                            if latest_version:
                                # 解析版本号并递增
                                try:
                                    version_parts = latest_version.code.split('.')
                                    if len(version_parts) >= 3:
                                        patch = int(version_parts[2]) + 1
                                        new_version_code = f"{version_parts[0]}.{version_parts[1]}.{patch}"
                                    else:
                                        new_version_code = f"v1.0.{int(latest_version.code.split('.')[-1]) + 1}"
                                except:
                                    # 如果解析失败，使用时间戳
                                    new_version_code = f"v1.0.{int(datetime.now().timestamp())}"
                            else:
                                # 如果是第一个版本
                                new_version_code = "v1.0.0"

                            # 创建新的version记录
                            version_data = VersionCreate(
                                code=new_version_code,
                                module_id=module.id,
                                msg=commit_msg,
                                commit=commit_sha
                            )

                            new_version = await version_repo.create_version(
                                data=version_data
                            )

                            logger.info(f"[Auto Commit] Created version: {new_version_code} (ID: {new_version.id})")
                            yield f"data: {json.dumps({'type': 'version', 'version_code': new_version_code, 'version_id': new_version.id})}\n\n"

                            # 更新module的latest_commit_id
                            from app.db.schemas.module import ModuleUpdate
                            module_update = ModuleUpdate(latest_commit_id=commit_sha)
                            await module_repo.update_module(
                                module_id=module.id,
                                data=module_update,
                                updated_by="system"
                            )

                            logger.info(f"[Auto Commit] Updated module latest_commit_id: {commit_sha}")
                            yield f"data: {json.dumps({'type': 'info', 'content': 'Successfully updated module version tracking'})}\n\n"
                        else:
                            logger.warning(f"[Auto Commit] No module found for session_id: {session_id}")
                            yield f"data: {json.dumps({'type': 'warning', 'content': 'No module linked to this session'})}\n\n"

                    else:
                        logger.info("[Auto Commit] No changes detected in workspace")

                except Exception as e:
                    logger.error(f"[Auto Commit] Error during auto-commit: {e}", exc_info=True)
                    yield f"data: {json.dumps({'type': 'error', 'content': f'Auto-commit failed: {str(e)}'})}\n\n"

            # 发送完成信号
            yield f"data: {json.dumps({'type': 'response_complete'})}\n\n"

        except Exception as e:
            logger.error(f"[SSE] Error during chat: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    finally:
        # 标记会话为非活跃
        session_manager.stop_session(session_id)


@chat_router.post(
    "/stream/auto-commit/{session_id}",
    summary="SSE流式聊天（自动提交）",
    operation_id="chat_stream_auto_commit"
)
async def chat_stream_auto_commit(
        session_id: str = Path(..., description="Session ID"),
        request: ChatRequest = Body(...),
):
    """
    SSE流式聊天端点（带自动commit功能）

    该端点会在Claude对workspace进行修改后：
    1. 自动检测代码变更
    2. 自动创建Git commit
    3. 根据session_id找到关联的module
    4. 创建新的version记录
    5. 更新module的latest_commit_id

    使用Server-Sent Events进行流式响应
    客户端应使用EventSource连接到此端点
    """
    # 获取会话信息
    try:
        session = await session_repo.get_session_by_id(session_id)

        if not session:
            return {"error": "Session not found"}

        workspace_path = session.workspace_path
        logger.info(f"[SSE Auto-Commit] Starting chat for session: {session.name}")

    except Exception as e:
        logger.error(f"[SSE Auto-Commit] Database error: {e}")
        return {"error": f"Database error: {str(e)}"}

    # 返回SSE流
    return StreamingResponse(
        chat_stream_with_auto_commit_generator(session_id, request.content, workspace_path),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用nginx缓冲
        }
    )


@chat_router.post(
    "/generate-spec/{session_id}",
    summary="生成开发文档",
    operation_id="generate_spec_document"
)
async def generate_spec_document(
        session_id: str = Path(..., description="Session ID"),
        request: SpecGenerationRequest = Body(...),
):
    """
    生成完整的开发文档（spec.md）

    该接口会：
    1. 根据用户输入的需求描述
    2. 构造专业的提示词
    3. 调用Claude生成规范的开发文档
    4. 返回markdown格式的文档内容

    开发文档包含：
    - 项目概述
    - 功能需求
    - 技术栈
    - 系统架构
    - 数据模型
    - API设计
    - 开发计划
    - 测试方案
    """
    try:
        # 获取会话信息
        session = await session_repo.get_session_by_id(session_id)
        if not session:
            from app.utils.model.response_model import BaseResponse
            return BaseResponse.not_found(message=f"会话 '{session_id}' 不存在")

        workspace_path = session.workspace_path or "/tmp"
        logger.info(f"[Spec Generation] Starting for session: {session.name}")

        # 构造专业的提示词
        spec_prompt = f"""你是一位专业的软件架构师和技术文档撰写专家。请根据以下需求描述，生成一份完整、规范的开发文档（spec.md）。

# 用户需求描述
{request.content}

# 文档要求
请生成一份完整的开发文档，返回md格式文本

# 输出要求
1. 使用标准的Markdown格式
2. 使用清晰的层级结构（# ## ### 等）
3. 对于架构图和流程图，使用Mermaid语法
4. 内容要详细、专业、可执行
5. 避免模糊和不确定的描述
6. 直接输出完整的Markdown文档，不要有任何的解释或前言

请开始生成开发文档："""

        # 创建Claude服务（使用一个临时的session_id来避免干扰正常对话）
        spec_generation_session_id = f"{session_id}_spec_gen"
        claude_service = await session_claude_manager.get_service(
            session_id=spec_generation_session_id,
            workspace_path=workspace_path,
        )

        # 调用非流式chat方法获取完整响应
        logger.info("[Spec Generation] Sending request to Claude...")
        spec_content = ""
        async for chat_msg in claude_service.chat_stream(
                spec_prompt,
                session_id=session_id,
        ):
            # 收集文本用于保存
            if chat_msg.type == "text":
                spec_content += chat_msg.content + "\n"

        # 清理临时session
        await session_claude_manager.close_session(spec_generation_session_id)

        logger.info(f"[Spec Generation] Generated document length: {len(spec_content)} characters")

        # 返回结果
        from app.utils.model.response_model import BaseResponse
        return BaseResponse.success(
            data={
                "session_id": session_id,
                "content": spec_content,
                "length": len(spec_content),
                "format": "markdown"
            },
            message="开发文档生成成功"
        )

    except Exception as e:
        logger.error(f"[Spec Generation] Error: {e}", exc_info=True)
        from app.utils.model.response_model import BaseResponse
        return BaseResponse.error(message=f"生成开发文档失败: {str(e)}")