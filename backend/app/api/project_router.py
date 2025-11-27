"""
Project API Router

项目管理相关的API路由定义
包括项目CRUD、代码拉取、容器管理等功能
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
    owner: int = Query(None, description="Filter by owner ID"),
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

    创建流程：
    1. 生成唯一的 session_id
    2. 创建工作空间目录
    3. 创建 Docker 容器（可选）
    4. 克隆 Git 仓库到工作空间
    5. 返回项目信息
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


@project_router.get(
    "/session/{session_id}",
    summary="根据Session ID获取项目",
    operation_id="get_project_by_session_id"
)
async def get_project_by_session_id(
    session_id: str = Path(..., description="Session ID")
):
    """根据 session_id 获取项目详情"""
    return await project_service.get_project_by_session_id(session_id)


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

    清理内容：
    - 停止并删除 Docker 容器
    - 删除工作空间目录
    - 删除数据库记录
    """
    return await project_service.delete_project(project_id)


@project_router.post(
    "/{project_id}/pull",
    summary="拉取项目代码",
    operation_id="pull_project_code"
)
async def pull_project_code(
    project_id: int = Path(..., description="Project ID")
):
    """
    拉取项目最新代码

    从 Git 仓库拉取最新代码到工作空间
    """
    return await project_service.pull_project_code(project_id)


@project_router.post(
    "/{project_id}/container/restart",
    summary="重启项目容器",
    operation_id="restart_project_container"
)
async def restart_project_container(
    project_id: int = Path(..., description="Project ID")
):
    """
    重启项目的 Docker 容器

    用于解决容器故障或应用环境配置变更后的重启需求
    """
    return await project_service.restart_project_container(project_id)
