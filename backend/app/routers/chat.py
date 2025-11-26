"""
Chat API Router

聊天相关的API路由定义
WebSocket用于实时聊天，HTTP用于历史记录和统计
"""

import json
import asyncio
import logging
from typing import Optional, Dict
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.db.repository import SessionRepository, MessageRepository
from app.services import ClaudeService, ChatMessage, session_claude_manager, ChatService
from app.config import get_settings

# 创建路由器
chat_router = APIRouter(prefix="/chat", tags=["chat"])

settings = get_settings()
logger = logging.getLogger(__name__)

# Repository和Service实例
session_repo = SessionRepository()
message_repo = MessageRepository()
chat_service = ChatService()


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, session_id: str, websocket: WebSocket):
        """注册WebSocket连接"""
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected for session: {session_id}")
    
    def disconnect(self, session_id: str):
        """注销WebSocket连接"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected for session: {session_id}")
    
    async def send_message(self, session_id: str, message: dict):
        """发送消息到指定会话"""
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)
    
    def is_connected(self, session_id: str) -> bool:
        """检查会话是否已连接"""
        return session_id in self.active_connections


manager = ConnectionManager()


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
# WebSocket Route
# ===================

@chat_router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket聊天端点，支持流式响应
    
    协议:
    - 客户端发送: {"type": "message", "content": "..."}
    - 客户端发送: {"type": "ping"}
    - 客户端发送: {"type": "interrupt"}
    - 服务端发送: {"type": "connected", "session_id": "..."}
    - 服务端发送: {"type": "text", "content": "..."}
    - 服务端发送: {"type": "tool_use", "tool_name": "...", "tool_input": {...}}
    - 服务端发送: {"type": "response_complete"}
    - 服务端发送: {"type": "error", "content": "..."}
    """
    
    # 先接受WebSocket连接
    await websocket.accept()
    logger.info(f"[WS] Connection accepted for session: {session_id}")
    
    # 获取会话信息
    try:
        session = await session_repo.get_session_by_id(session_id)
        
        if not session:
            logger.warning(f"[WS] Session not found: {session_id}")
            await websocket.send_json({
                "type": "error",
                "content": f"Session not found: {session_id}",
            })
            await websocket.close(code=4004, reason="Session not found")
            return
        
        workspace_path = session.workspace_path
        logger.info(f"[WS] Found session: {session.name}, workspace: {workspace_path}")
        
    except Exception as e:
        logger.error(f"[WS] Database error: {e}")
        await websocket.send_json({
            "type": "error",
            "content": f"Database error: {str(e)}",
        })
        await websocket.close(code=4005, reason="Database error")
        return
    
    await manager.connect(session_id, websocket)
    
    # 发送连接确认
    await websocket.send_json({
        "type": "connected",
        "session_id": session_id,
        "message": "Connected to chat session",
    })
    
    try:
        while True:
            # 等待用户消息
            data = await websocket.receive_json()
            logger.debug(f"[WS] Received data: {data}")
            
            message_type = data.get("type")
            
            if message_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            
            if message_type == "message":
                user_message = data.get("content", "")
                
                if not user_message.strip():
                    continue
                
                logger.info(f"[WS] User message: {user_message[:50]}...")
                
                # 保存用户消息
                await save_message(session_id, "user", user_message)
                
                # 发送确认
                await websocket.send_json({
                    "type": "user_message_received",
                    "content": user_message,
                })
                
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
                        msg_dict = chat_message_to_dict(chat_msg)
                        await websocket.send_json(msg_dict)
                        
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
                    await websocket.send_json({
                        "type": "response_complete",
                    })
                    
                except Exception as e:
                    logger.error(f"[WS] Error during chat: {e}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "content": str(e),
                    })
            
            elif message_type == "interrupt":
                # 处理中断信号
                claude_service = await session_claude_manager.get_service(
                    session_id=session_id,
                    workspace_path=workspace_path,
                )
                await claude_service.interrupt()
                await websocket.send_json({
                    "type": "interrupted",
                    "message": "Request interrupted",
                })
    
    except WebSocketDisconnect:
        logger.info(f"[WS] Client disconnected: {session_id}")
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"[WS] Error: {e}", exc_info=True)
        manager.disconnect(session_id)
        raise


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
