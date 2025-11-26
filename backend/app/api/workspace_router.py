"""
Workspace API Router

工作空间文件操作相关的API路由定义
只负责路由定义，所有业务逻辑在service层
"""

from fastapi import APIRouter, Query, Path, Body
from pydantic import BaseModel

from app.service.workspace_service import WorkspaceService

# 创建路由器
workspace_router = APIRouter(prefix="/workspace", tags=["workspace"])

# 创建service实例
workspace_service = WorkspaceService()


# ===================
# Request Models
# ===================

class WriteFileRequest(BaseModel):
    path: str
    content: str


# ===================
# File Routes
# ===================

@workspace_router.get(
    "/{session_id}/files",
    summary="列出文件",
    operation_id="list_workspace_files"
)
async def list_files(
    session_id: str = Path(..., description="Session ID"),
    path: str = Query("", description="Relative path in workspace"),
):
    """列出工作空间目录下的文件"""
    return await workspace_service.list_files(session_id=session_id, path=path)


@workspace_router.get(
    "/{session_id}/file",
    summary="读取文件",
    operation_id="read_workspace_file"
)
async def read_file(
    session_id: str = Path(..., description="Session ID"),
    path: str = Query(..., description="Relative path to file"),
):
    """读取工作空间中的文件内容"""
    return await workspace_service.read_file(session_id=session_id, path=path)


@workspace_router.put(
    "/{session_id}/file",
    summary="写入文件",
    operation_id="write_workspace_file"
)
async def write_file(
    session_id: str = Path(..., description="Session ID"),
    data: WriteFileRequest = Body(...),
):
    """写入文件内容到工作空间"""
    return await workspace_service.write_file(
        session_id=session_id,
        path=data.path,
        content=data.content,
    )


@workspace_router.delete(
    "/{session_id}/file",
    summary="删除文件",
    operation_id="delete_workspace_file"
)
async def delete_file(
    session_id: str = Path(..., description="Session ID"),
    path: str = Query(..., description="Relative path to file"),
):
    """删除工作空间中的文件"""
    return await workspace_service.delete_file(session_id=session_id, path=path)
