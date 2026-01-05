"""
Project API Router

项目管理相关的API路由定义
只包括项目基本CRUD操作
"""

from typing import Optional
from fastapi import APIRouter, Query, Path, Depends
from app.service.project_service import ProjectService
from app.db.schemas import ProjectCreate, ProjectUpdate
from app.utils.auth.dependencies import get_optional_user_id

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
    user_id: Optional[str] = Depends(get_optional_user_id),
):
    """
    获取项目列表（分页，自动按当前用户筛选）

    从Authorization header中的JWT token自动提取user_id进行过滤
    如果没有提供token，则返回所有项目
    """
    return await project_service.list_projects(skip=skip, limit=limit, owner=user_id)


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
    project_id: int = Path(..., description="Project ID"),
    user_id: Optional[str] = Depends(get_optional_user_id),
):
    """
    根据ID获取项目详情

    如果提供了JWT token，会验证项目是否属于当前用户
    如果没有提供token，则允许访问任何项目
    """
    return await project_service.get_project(project_id, user_id=user_id)


@project_router.get(
    "/code/{code}",
    summary="根据代码获取项目",
    operation_id="get_project_by_code"
)
async def get_project_by_code(
    code: str = Path(..., description="Project code"),
    user_id: Optional[str] = Depends(get_optional_user_id),
):
    """
    根据项目代码获取项目详情

    如果提供了JWT token，会验证项目是否属于当前用户
    如果没有提供token，则允许访问任何项目
    """
    return await project_service.get_project_by_code(code, user_id=user_id)


@project_router.put(
    "/{project_id}",
    summary="更新项目",
    operation_id="update_project"
)
async def update_project(
    project_id: int = Path(..., description="Project ID"),
    data: ProjectUpdate = None,
    user_id: Optional[str] = Depends(get_optional_user_id),
):
    """
    更新项目信息

    如果提供了JWT token，会验证项目是否属于当前用户
    如果没有提供token，则允许更新任何项目
    """
    return await project_service.update_project(project_id, data, user_id=user_id)


@project_router.delete(
    "/{project_id}",
    summary="删除项目",
    operation_id="delete_project"
)
async def delete_project(
    project_id: int = Path(..., description="Project ID"),
    user_id: Optional[str] = Depends(get_optional_user_id),
):
    """
    删除项目（级联删除关联的模块和版本）

    如果提供了JWT token，会验证项目是否属于当前用户
    如果没有提供token，则允许删除任何项目
    """
    return await project_service.delete_project(project_id, user_id=user_id)


@project_router.get(
    "/{project_id}/leaf-modules/content-status",
    summary="获取项目叶子模块状态",
    operation_id="get_leaf_modules_content_status"
)
async def get_leaf_modules_content_status(
    project_id: int = Path(..., description="Project ID"),
    user_id: Optional[str] = Depends(get_optional_user_id),
):
    """
    获取项目下所有叶子模块(POINT类型)的ID和content_status列表

    如果提供了JWT token，会验证项目是否属于当前用户
    如果没有提供token，则允许访问任何项目

    返回格式：{"code": 200, "data": [{"id": 1, "content_status": "PENDING"}, ...], "total": 10}
    """
    return await project_service.get_leaf_modules_content_status(project_id, user_id=user_id)
