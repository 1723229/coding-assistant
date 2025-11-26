"""
Session API Router

会话管理相关的API路由定义
只负责路由定义，所有业务逻辑在service层
"""

from fastapi import APIRouter, Query, Path
from app.service.session_service import SessionService
from app.db.schemas import SessionCreate, SessionUpdate

# 创建路由器
session_router = APIRouter(prefix="/sessions", tags=["sessions"])

# 创建service实例
session_service = SessionService()


@session_router.get(
    "",
    summary="获取会话列表",
    operation_id="list_sessions"
)
async def list_sessions(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records"),
):
    """获取会话列表（分页）"""
    return await session_service.list_sessions(skip=skip, limit=limit)


@session_router.post(
    "",
    summary="创建新会话",
    operation_id="create_session"
)
async def create_session(data: SessionCreate):
    """创建新会话"""
    return await session_service.create_session(data)


@session_router.get(
    "/{session_id}",
    summary="获取会话详情",
    operation_id="get_session"
)
async def get_session(
    session_id: str = Path(..., description="Session ID")
):
    """根据ID获取会话详情"""
    return await session_service.get_session(session_id)


@session_router.put(
    "/{session_id}",
    summary="更新会话",
    operation_id="update_session"
)
async def update_session(
    session_id: str = Path(..., description="Session ID"),
    data: SessionUpdate = None,
):
    """更新会话信息"""
    return await session_service.update_session(session_id, data)


@session_router.delete(
    "/{session_id}",
    summary="删除会话",
    operation_id="delete_session"
)
async def delete_session(
    session_id: str = Path(..., description="Session ID")
):
    """删除会话（软删除）"""
    return await session_service.delete_session(session_id)


@session_router.get(
    "/{session_id}/messages",
    summary="获取会话消息",
    operation_id="get_session_messages"
)
async def get_session_messages(
    session_id: str = Path(..., description="Session ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records"),
):
    """获取会话的消息列表"""
    return await session_service.get_session_messages(session_id, skip=skip, limit=limit)
