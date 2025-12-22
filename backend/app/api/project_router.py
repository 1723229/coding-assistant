"""
Project API Router

项目管理相关的API路由定义
只包括项目基本CRUD操作
"""

from fastapi import APIRouter, Query, Path
from app.service.project_service import ProjectService
from app.db.schemas import ProjectCreate, ProjectUpdate

# 创建路由器
project_router = APIRouter(prefix="/projects", tags=["projects"])

# 创建service实例
project_service = ProjectService()


@project_router.get(
    "",
    summary="获取项目列表",
    operation_id="list_projects"
)
async def list_projects(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records"),
    owner: str = Query(None, description="Filter by owner ID"),
):
    """获取项目列表（分页，可按所有者筛选）"""
    return await project_service.list_projects(skip=skip, limit=limit, owner=owner)


@project_router.post(
    "",
    summary="创建新项目",
    operation_id="create_project"
)
async def create_project(data: ProjectCreate):
    """
    创建新项目

    只创建项目记录，不涉及工作空间和容器
    """
    return await project_service.create_project(data)


@project_router.get(
    "/{project_id}",
    summary="获取项目详情",
    operation_id="get_project"
)
async def get_project(
    project_id: int = Path(..., description="Project ID")
):
    """根据ID获取项目详情"""
    return await project_service.get_project(project_id)


@project_router.get(
    "/code/{code}",
    summary="根据代码获取项目",
    operation_id="get_project_by_code"
)
async def get_project_by_code(
    code: str = Path(..., description="Project code")
):
    """根据项目代码获取项目详情"""
    return await project_service.get_project_by_code(code)


@project_router.put(
    "/{project_id}",
    summary="更新项目",
    operation_id="update_project"
)
async def update_project(
    project_id: int = Path(..., description="Project ID"),
    data: ProjectUpdate = None,
):
    """更新项目信息"""
    return await project_service.update_project(project_id, data)


@project_router.delete(
    "/{project_id}",
    summary="删除项目",
    operation_id="delete_project"
)
async def delete_project(
    project_id: int = Path(..., description="Project ID")
):
    """
    删除项目（级联删除关联的模块和版本）

    只删除数据库记录
    """
    return await project_service.delete_project(project_id)


@project_router.get(
    "/{project_id}/leaf-modules/content-status",
    summary="获取项目叶子模块状态",
    operation_id="get_leaf_modules_content_status"
)
async def get_leaf_modules_content_status(
    project_id: int = Path(..., description="Project ID")
):
    """
    获取项目下所有叶子模块(POINT类型)的ID和content_status列表

    返回格式：{"code": 200, "data": [{"id": 1, "content_status": "PENDING"}, ...], "total": 10}
    """
    return await project_service.get_leaf_modules_content_status(project_id)
