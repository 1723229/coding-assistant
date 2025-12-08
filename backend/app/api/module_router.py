"""
Module API Router

模块管理相关的API路由定义
支持 NODE 和 POINT 类型，POINT 类型管理 workspace 和容器
"""

from fastapi import APIRouter, Query, Path
from fastapi.responses import StreamingResponse
from app.service.module_service import ModuleService
from app.db.schemas import ModuleCreate, ModuleUpdate

# 创建路由器
module_router = APIRouter(prefix="/modules", tags=["modules"])

# 创建service实例
module_service = ModuleService()


@module_router.get(
    "/project/{project_id}",
    summary="获取项目的模块列表",
    operation_id="list_modules"
)
async def list_modules(
    project_id: int = Path(..., description="Project ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records"),
):
    """获取项目的模块列表（平铺结构）"""
    return await module_service.list_modules(project_id=project_id, skip=skip, limit=limit)


@module_router.get(
    "/project/{project_id}/tree",
    summary="获取项目的模块树",
    operation_id="get_module_tree"
)
async def get_module_tree(
    project_id: int = Path(..., description="Project ID")
):
    """获取项目的模块树形结构"""
    return await module_service.get_module_tree(project_id=project_id)


@module_router.post(
    "",
    summary="创建新模块",
    operation_id="create_module"
)
async def create_module(data: ModuleCreate):
    """
    创建新模块

    - NODE 类型：只创建记录，URL 与子节点共享
    - POINT 类型：创建 session，拉取代码到 workspace
    """
    return await module_service.create_module(data)


@module_router.post(
    "/stream",
    summary="创建新模块（流式）",
    operation_id="create_module_stream"
)
async def create_module_stream(data: ModuleCreate):
    """
    创建新模块（SSE流式）

    实时返回创建进度，用于POINT类型模块的长时间操作

    事件类型：
    - connected: 连接建立
    - step: 步骤进度更新
    - error: 错误信息
    - complete: 创建完成
    """
    return StreamingResponse(
        module_service.create_module_stream(data),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@module_router.post(
    "/optimize/{session_id}/stream",
    summary="优化模块代码（流式）",
    operation_id="optimize_module_stream"
)
async def optimize_module_stream(
    session_id: str = Path(..., description="Session ID"),
    optimization_request: dict = None
):
    """
    优化已创建的POINT类型模块（SSE流式）

    根据用户新的需求对现有代码进行优化，实时返回优化进度

    请求体:
    {
        "content": "优化需求描述",
        "updated_by": "用户标识"
    }

    事件类型：
    - connected: 连接建立
    - step: 步骤进度更新
    - error: 错误信息
    - complete: 优化完成
    """
    content = optimization_request.get("content") if optimization_request else ""
    updated_by = optimization_request.get("updated_by") if optimization_request else None

    return StreamingResponse(
        module_service.optimize_module_stream(session_id, content, updated_by),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@module_router.post(
    "/build/{session_id}/stream",
    summary="优化模块代码（流式）",
    operation_id="build_module_stream"
)
async def build_module_stream(
    session_id: str = Path(..., description="Session ID"),
    optimization_request: dict = None
):
    """
    优化已创建的POINT类型模块（SSE流式）

    事件类型：
    - connected: 连接建立
    - step: 步骤进度更新
    - error: 错误信息
    - complete: 优化完成
    """
    content = optimization_request.get("content") if optimization_request else ""
    updated_by = optimization_request.get("updated_by") if optimization_request else None
    return StreamingResponse(
        module_service.build_module_stream(session_id, content, updated_by),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@module_router.get(
    "/{module_id}",
    summary="获取模块详情",
    operation_id="get_module"
)
async def get_module(
    module_id: int = Path(..., description="Module ID")
):
    """根据ID获取模块详情"""
    return await module_service.get_module(module_id)


@module_router.get(
    "/session/{session_id}",
    summary="根据Session ID获取模块",
    operation_id="get_module_by_session_id"
)
async def get_module_by_session_id(
    session_id: str = Path(..., description="Session ID")
):
    """根据 session_id 获取 POINT 类型模块详情"""
    return await module_service.get_module_by_session_id(session_id)


@module_router.put(
    "/{module_id}",
    summary="更新模块",
    operation_id="update_module"
)
async def update_module(
    module_id: int = Path(..., description="Module ID"),
    data: ModuleUpdate = None,
):
    """更新模块信息"""
    return await module_service.update_module(module_id, data)


@module_router.delete(
    "/{module_id}",
    summary="删除模块",
    operation_id="delete_module"
)
async def delete_module(
    module_id: int = Path(..., description="Module ID")
):
    """
    删除模块（级联删除子模块）

    POINT 类型会清理 workspace 和容器
    """
    return await module_service.delete_module(module_id)


@module_router.post(
    "/{module_id}/pull",
    summary="拉取模块代码",
    operation_id="pull_module_code"
)
async def pull_module_code(
    module_id: int = Path(..., description="Module ID")
):
    """
    拉取 POINT 类型模块的最新代码

    从 Git 仓库拉取最新代码到 workspace
    """
    return await module_service.pull_module_code(module_id)


@module_router.post(
    "/{module_id}/container/restart",
    summary="重启模块容器",
    operation_id="restart_module_container"
)
async def restart_module_container(
    module_id: int = Path(..., description="Module ID")
):
    """
    重启 POINT 类型模块的 Docker 容器

    用于解决容器故障或应用环境配置变更后的重启需求
    """
    return await module_service.restart_module_container(module_id)
