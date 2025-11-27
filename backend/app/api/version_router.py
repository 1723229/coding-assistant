"""
Version API Router

版本管理相关的API路由定义
"""

from fastapi import APIRouter, Query, Path
from app.service.version_service import VersionService
from app.db.schemas import VersionCreate, VersionUpdate

# 创建路由器
version_router = APIRouter(prefix="/versions", tags=["versions"])

# 创建service实例
version_service = VersionService()


@version_router.get(
    "/project/{project_id}",
    summary="获取项目的版本列表",
    operation_id="list_versions"
)
async def list_versions(
    project_id: int = Path(..., description="Project ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records"),
):
    """获取项目的版本列表（按创建时间倒序）"""
    return await version_service.list_versions(project_id=project_id, skip=skip, limit=limit)


@version_router.get(
    "/project/{project_id}/latest",
    summary="获取项目的最新版本",
    operation_id="get_latest_version"
)
async def get_latest_version(
    project_id: int = Path(..., description="Project ID")
):
    """获取项目的最新版本"""
    return await version_service.get_latest_version(project_id=project_id)


@version_router.get(
    "/project/{project_id}/code/{code}",
    summary="根据版本编号获取版本",
    operation_id="get_version_by_code"
)
async def get_version_by_code(
    project_id: int = Path(..., description="Project ID"),
    code: str = Path(..., description="Version code")
):
    """根据项目ID和版本编号获取版本详情"""
    return await version_service.get_version_by_code(project_id=project_id, code=code)


@version_router.post(
    "",
    summary="创建新版本",
    operation_id="create_version"
)
async def create_version(data: VersionCreate):
    """创建新版本"""
    return await version_service.create_version(data)


@version_router.get(
    "/{version_id}",
    summary="获取版本详情",
    operation_id="get_version"
)
async def get_version(
    version_id: int = Path(..., description="Version ID")
):
    """根据ID获取版本详情"""
    return await version_service.get_version(version_id)


@version_router.put(
    "/{version_id}",
    summary="更新版本",
    operation_id="update_version"
)
async def update_version(
    version_id: int = Path(..., description="Version ID"),
    data: VersionUpdate = None,
):
    """更新版本信息"""
    return await version_service.update_version(version_id, data)


@version_router.delete(
    "/{version_id}",
    summary="删除版本",
    operation_id="delete_version"
)
async def delete_version(
    version_id: int = Path(..., description="Version ID")
):
    """删除版本"""
    return await version_service.delete_version(version_id)
