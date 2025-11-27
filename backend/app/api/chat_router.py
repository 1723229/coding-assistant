"""
Chat API Router

聊天相关的API路由定义
使用SSE (Server-Sent Events) 进行流式聊天，HTTP用于历史记录和统计
"""

import asyncio
import json
import logging
from typing import Optional, Dict, AsyncGenerator

from app.config import get_settings
from app.core.claude_service import ClaudeService, ChatMessage, session_claude_manager
from app.db.repository import SessionRepository, MessageRepository
from app.service.chat_service import ChatService
from fastapi import APIRouter, Query, Body, Path
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# 创建路由器
chat_router = APIRouter(prefix="/chat", tags=["chat"])

settings = get_settings()
logger = logging.getLogger(__name__)

# Repository和Service实例
session_repo = SessionRepository()
message_repo = MessageRepository()
chat_service = ChatService()


# ===================
# Request Models
# ===================

class ChatRequest(BaseModel):
    """聊天请求模型"""
    content: str


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
        session_id: str = Path(..., description="Session ID"),
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
