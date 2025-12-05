"""
Chat API Router

聊天相关的API路由定义
使用SSE (Server-Sent Events) 进行流式聊天，HTTP用于历史记录和统计

All execution happens in sandbox containers.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, AsyncGenerator
from datetime import datetime

from app.config import get_settings
from app.core.claude_service import ChatMessage, session_manager
from app.core.github_service import GitHubService
from app.db.repository import SessionRepository, MessageRepository, ModuleRepository, VersionRepository
from app.db.schemas.version import VersionCreate
from app.service.chat_service import ChatService
from fastapi import APIRouter, Query, Body, Path
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.utils.prompt.prompt_build import generate_code_from_spec
from app.utils.model.response_model import BaseResponse

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
    task_type: Optional[str] = None  # OpenSpec 任务类型: "spec", "preview", "build"

class SpecGenerationRequest(BaseModel):
    """Spec文档生成请求模型"""
    content: str = Field(..., description="功能需求描述")


# ===================
# Active Sessions Tracking
# ===================

class ActiveSessionTracker:
    """跟踪活跃的流式会话"""

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


active_session_tracker = ActiveSessionTracker()


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
        task_type: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    SSE流式生成器

    发送格式: data: {json}\n\n
    
    Args:
        session_id: 会话ID
        user_message: 用户消息
        workspace_path: 工作空间路径
        task_type: OpenSpec 任务类型 ("spec", "preview", "build")
    """
    try:
        # 标记会话为活跃
        active_session_tracker.start_session(session_id)

        # 立即发送连接确认
        yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
        await asyncio.sleep(0)

        # 保存用户消息
        await save_message(session_id, "user", user_message)

        # 获取沙箱服务
        sandbox_service = await session_manager.get_service(
            session_id=session_id,
            workspace_path=workspace_path,
        )

        logger.info(f"[SSE] Starting chat for session: {session_id}, task_type: {task_type}")

        # 流式响应
        full_response = []
        try:
            async for chat_msg in sandbox_service.chat_stream(
                    user_message,
                    session_id=session_id,
                    task_type=task_type,
            ):
                # 检查会话是否被中断
                if not active_session_tracker.is_active(session_id):
                    yield f"data: {json.dumps({'type': 'interrupted', 'message': 'Stream interrupted'})}\n\n"
                    break

                msg_dict = chat_message_to_dict(chat_msg)
                yield f"data: {json.dumps(msg_dict)}\n\n"

                # 收集文本用于保存
                if chat_msg.type in ("text", "text_delta"):
                    full_response.append(chat_msg.content)

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
        active_session_tracker.stop_session(session_id)


@chat_router.post(
    "/stream/{session_id}",
    summary="SSE流式聊天",
    operation_id="chat_stream"
)
async def chat_stream(
        session_id: str = Path(..., description="Session ID"),
        request: ChatRequest = Body(...),
):
    """
    SSE流式聊天端点

    使用Server-Sent Events进行流式响应
    """
    try:
        session = await session_repo.get_session_by_id(session_id)

        if not session:
            return {"error": "Session not found"}

        workspace_path = session.workspace_path
        logger.info(f"[SSE] Starting chat for session: {session.name}")

    except Exception as e:
        logger.error(f"[SSE] Database error: {e}")
        return {"error": f"Database error: {str(e)}"}

    return StreamingResponse(
        chat_stream_generator(session_id, request.content, workspace_path, request.task_type),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
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
        active_session_tracker.stop_session(session_id)

        # 中断沙箱服务
        sandbox_service = await session_manager.get_service(
            session_id=session_id,
            workspace_path="",
        )
        await sandbox_service.interrupt()

        return {"message": "Chat stream interrupted", "session_id": session_id}
    except Exception as e:
        logger.error(f"Failed to interrupt chat: {e}")
        return {"error": str(e)}


# ===================
# Container Management Routes
# ===================

@chat_router.get(
    "/container/{session_id}/status",
    summary="获取容器状态",
    operation_id="get_container_status"
)
async def get_container_status(session_id: str = Path(..., description="Session ID")):
    """获取会话容器的状态"""
    try:
        from app.core.executor import get_sandbox_executor
        executor = get_sandbox_executor()
        status = await executor.get_container_status(session_id)
        return status
    except Exception as e:
        logger.error(f"Failed to get container status: {e}")
        return {"error": str(e)}


@chat_router.get(
    "/container/{session_id}/health",
    summary="容器健康检查",
    operation_id="container_health_check"
)
async def container_health_check(session_id: str = Path(..., description="Session ID")):
    """对会话容器进行健康检查"""
    try:
        from app.core.executor import get_sandbox_executor
        executor = get_sandbox_executor()
        health = await executor.health_check(session_id)
        return health
    except Exception as e:
        logger.error(f"Failed to perform health check: {e}")
        return {"error": str(e)}


@chat_router.delete(
    "/container/{session_id}",
    summary="删除容器",
    operation_id="delete_container"
)
async def delete_container(session_id: str = Path(..., description="Session ID")):
    """删除会话容器"""
    try:
        from app.core.executor import get_sandbox_executor
        executor = get_sandbox_executor()
        success = await executor.cleanup(session_id)

        if success:
            return {"message": f"Container for session {session_id} deleted", "status": "success"}
        else:
            return {"message": f"Container for session {session_id} not found", "status": "not_found"}
    except Exception as e:
        logger.error(f"Failed to delete container: {e}")
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



@chat_router.post(
    "/auto-commit/{session_id}",
    summary="根据spec.md生成代码",
    operation_id="chat_stream_auto_commit"
)
async def chat_stream_auto_commit(
        session_id: str = Path(..., description="Session ID"),
        request: ChatRequest = Body(...),
):
    """
    根据md生成代码（带自动commit功能）

    该端点会在Claude对workspace进行修改后：
    1. 自动检测代码变更
    2. 自动创建Git commit
    3. 根据session_id找到关联的module
    4. 创建新的version记录
    5. 更新module的latest_commit_id
    """
    # 获取会话信息
    try:
        session = await session_repo.get_session_by_id(session_id)
        module = await module_repo.get_module_by_session_id(session_id=session_id)
        if not session:
            return {"error": "Session not found"}
        if not module:
            return {"error": "Module not found"}

        workspace_path = session.workspace_path
        logger.info(f"[SSE Auto-Commit] Starting chat for session: {session.name}")
        commit_id = await generate_code_from_spec(
            spec_content=request.content,
            session_id=session_id,
            workspace_path=workspace_path,
            module_name=module.name,
            module_code=module.code,
        )
        if commit_id:
            logger.info(f"[SSE Auto-Commit] Commit ID: {commit_id}")
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
                commit_message = f"[SpecCoding Auto Commit] - {module.name} ({module.code})-{new_version_code} 功能实现"
                # 创建新的version记录
                version_data = VersionCreate(
                    code=new_version_code,
                    module_id=module.id,
                    msg=commit_message,
                    commit=commit_id
                )

                new_version = await version_repo.create_version(
                    data=version_data
                )
                logger.info(f"[Auto Commit] Created version: {new_version_code} (ID: {new_version.id})")

                # 更新module的latest_commit_id
                from app.db.schemas.module import ModuleUpdate
                module_update = ModuleUpdate(latest_commit_id=commit_id)
                await module_repo.update_module(
                    module_id=module.id,
                    data=module_update,
                )

                logger.info(f"[Auto Commit] Updated module latest_commit_id: {commit_id}")
                # 返回结果
                return BaseResponse.success(data=json.dumps({'type': 'success', 'content': 'Successfully updated module version tracking'}))
    except Exception as e:
        logger.error(f"[Auto-Commit] Database error: {e}")
        return BaseResponse.error(message=f"生成开发文档失败: {str(e)}")


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

        # 创建沙箱服务（使用一个临时的session_id来避免干扰正常对话）
        spec_generation_session_id = f"{session_id}_spec_gen"
        sandbox_service = await session_manager.get_service(
            session_id=spec_generation_session_id,
            workspace_path=workspace_path,
        )

        # 调用流式chat方法获取完整响应
        logger.info("[Spec Generation] Sending request to sandbox...")
        spec_content = ""
        async for chat_msg in sandbox_service.chat_stream(
                spec_prompt,
                session_id=spec_generation_session_id,
        ):
            # 收集文本用于保存
            if chat_msg.type == "text":
                spec_content += chat_msg.content + "\n"

        # 清理临时session
        await session_manager.close_session(spec_generation_session_id)

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