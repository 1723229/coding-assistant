"""
Chat service implementation

聊天相关的业务逻辑层
"""

import logging
from typing import Optional
from fastapi import Query

from app.config.logging_config import log_print
from app.utils.model.response_model import BaseResponse, ListResponse
from app.db.repository import SessionRepository, MessageRepository

logger = logging.getLogger(__name__)


class ChatService:
    """
    聊天服务类
    
    提供聊天相关的所有业务逻辑操作
    """
    
    def __init__(self):
        self.session_repo = SessionRepository()
        self.message_repo = MessageRepository()
    
    @log_print
    async def get_chat_history(
        self,
        session_id: str,
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, le=500, description="Maximum number of records"),
    ):
        """获取聊天历史"""
        try:
            messages = await self.message_repo.get_session_messages(
                session_id=session_id,
                skip=skip,
                limit=limit,
            )
            
            items = [
                {
                    "id": m.id,
                    "session_id": m.session_id,
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "tool_name": m.tool_name,
                }
                for m in messages
            ]
            
            return ListResponse.success(items=items, total=len(items))
        except Exception as e:
            return BaseResponse.error(message=f"获取聊天历史失败: {str(e)}")
    
    @log_print
    async def get_session_stats(self, session_id: str):
        """获取会话统计信息"""
        try:
            session = await self.session_repo.get_session_by_id(session_id)
            if not session:
                return BaseResponse.not_found(message=f"会话 '{session_id}' 不存在")
            
            # 获取消息统计
            messages = await self.message_repo.get_session_messages(
                session_id=session_id,
                skip=0,
                limit=10000,  # 获取所有消息来统计
            )
            
            user_messages = sum(1 for m in messages if m.role == "user")
            assistant_messages = sum(1 for m in messages if m.role == "assistant")
            tool_uses = sum(1 for m in messages if m.tool_name)
            
            return BaseResponse.success(
                data={
                    "session_id": session_id,
                    "total_messages": len(messages),
                    "user_messages": user_messages,
                    "assistant_messages": assistant_messages,
                    "tool_uses": tool_uses,
                },
                message="获取统计信息成功"
            )
        except Exception as e:
            return BaseResponse.error(message=f"获取统计信息失败: {str(e)}")
    
    @log_print
    async def get_all_stats(self):
        """获取所有会话的统计信息"""
        try:
            sessions = await self.session_repo.get_active_sessions(skip=0, limit=1000)
            
            total_sessions = len(sessions)
            active_sessions = sum(1 for s in sessions if s.is_active)
            
            # 统计总消息数
            total_messages = 0
            for session in sessions:
                messages = await self.message_repo.get_session_messages(
                    session_id=session.id,
                    skip=0,
                    limit=10000,
                )
                total_messages += len(messages)
            
            return BaseResponse.success(
                data={
                    "total_sessions": total_sessions,
                    "active_sessions": active_sessions,
                    "total_messages": total_messages,
                },
                message="获取统计信息成功"
            )
        except Exception as e:
            return BaseResponse.error(message=f"获取统计信息失败: {str(e)}")

