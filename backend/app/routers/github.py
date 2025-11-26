"""
GitHub API Router

GitHub相关的API路由定义
只负责路由定义，所有业务逻辑在service层
"""

from typing import Optional, List
from fastapi import APIRouter, Query, Path, Body
from pydantic import BaseModel

from app.services import GitHubApiService
from app.db.schemas import GitHubTokenCreate

# 创建路由器
github_router = APIRouter(prefix="/github", tags=["github"])

# 创建service实例
github_service = GitHubApiService()


# ===================
# Request Models
# ===================

class CloneRepoRequest(BaseModel):
    repo_url: str
    branch: Optional[str] = None


class CommitRequest(BaseModel):
    message: str
    files: Optional[List[str]] = None


class PushRequest(BaseModel):
    branch: Optional[str] = None


class CreateBranchRequest(BaseModel):
    branch_name: str
    checkout: bool = True


class CheckoutBranchRequest(BaseModel):
    branch_name: str


class CreatePRRequest(BaseModel):
    title: str
    body: str
    head_branch: str
    base_branch: Optional[str] = None


# ===================
# Token Management Routes
# ===================

@github_router.get(
    "/tokens",
    summary="获取Token列表",
    operation_id="list_github_tokens"
)
async def list_tokens():
    """获取所有GitHub tokens"""
    return await github_service.list_tokens()


@github_router.post(
    "/tokens",
    summary="创建Token",
    operation_id="create_github_token"
)
async def create_token(data: GitHubTokenCreate):
    """创建新的GitHub token"""
    return await github_service.create_token(data)


@github_router.delete(
    "/tokens/{token_id}",
    summary="删除Token",
    operation_id="delete_github_token"
)
async def delete_token(
    token_id: int = Path(..., description="Token ID")
):
    """删除GitHub token"""
    return await github_service.delete_token(token_id)


# ===================
# Repository Routes
# ===================

@github_router.get(
    "/repos",
    summary="获取仓库列表",
    operation_id="list_github_repos"
)
async def list_repos(
    query: Optional[str] = Query(None, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(30, ge=1, le=100, description="Items per page"),
):
    """获取用户的GitHub仓库列表"""
    return await github_service.list_repos(query=query, page=page, per_page=per_page)


@github_router.get(
    "/repos/info",
    summary="获取仓库信息",
    operation_id="get_github_repo_info"
)
async def get_repo_info(
    repo_url: str = Query(..., description="GitHub repository URL")
):
    """获取仓库信息"""
    return await github_service.get_repo_info(repo_url)


@github_router.post(
    "/{session_id}/clone",
    summary="克隆仓库",
    operation_id="clone_github_repo"
)
async def clone_repo(
    session_id: str = Path(..., description="Session ID"),
    data: CloneRepoRequest = Body(...),
):
    """克隆仓库到会话工作空间"""
    return await github_service.clone_repo(
        session_id=session_id,
        repo_url=data.repo_url,
        branch=data.branch,
    )


# ===================
# Local Git Routes
# ===================

@github_router.get(
    "/{session_id}/changes",
    summary="获取本地变更",
    operation_id="get_local_changes"
)
async def get_local_changes(
    session_id: str = Path(..., description="Session ID"),
    include_diff: bool = Query(False, description="Include diff content"),
):
    """获取本地变更"""
    return await github_service.get_local_changes(
        session_id=session_id,
        include_diff=include_diff,
    )


@github_router.get(
    "/{session_id}/diff",
    summary="获取文件差异",
    operation_id="get_file_diff"
)
async def get_file_diff(
    session_id: str = Path(..., description="Session ID"),
    file_path: str = Query(..., description="Path to file"),
):
    """获取文件差异"""
    return await github_service.get_file_diff(
        session_id=session_id,
        file_path=file_path,
    )


@github_router.post(
    "/{session_id}/commit",
    summary="提交变更",
    operation_id="commit_changes"
)
async def commit_changes(
    session_id: str = Path(..., description="Session ID"),
    data: CommitRequest = Body(...),
):
    """提交变更"""
    return await github_service.commit_changes(
        session_id=session_id,
        message=data.message,
        files=data.files,
    )


@github_router.post(
    "/{session_id}/push",
    summary="推送变更",
    operation_id="push_changes"
)
async def push_changes(
    session_id: str = Path(..., description="Session ID"),
    data: PushRequest = Body(default=None),
):
    """推送变更到远程"""
    branch = data.branch if data else None
    return await github_service.push_changes(
        session_id=session_id,
        branch=branch,
    )


@github_router.post(
    "/{session_id}/pull",
    summary="拉取变更",
    operation_id="pull_changes"
)
async def pull_changes(
    session_id: str = Path(..., description="Session ID"),
):
    """拉取远程变更"""
    return await github_service.pull_changes(session_id)


# ===================
# Branch Routes
# ===================

@github_router.get(
    "/{session_id}/branches",
    summary="获取分支列表",
    operation_id="list_branches"
)
async def list_branches(
    session_id: str = Path(..., description="Session ID"),
):
    """获取分支列表"""
    return await github_service.list_branches(session_id)


@github_router.post(
    "/{session_id}/branches",
    summary="创建分支",
    operation_id="create_branch"
)
async def create_branch(
    session_id: str = Path(..., description="Session ID"),
    data: CreateBranchRequest = Body(...),
):
    """创建新分支"""
    return await github_service.create_branch(
        session_id=session_id,
        branch_name=data.branch_name,
        checkout=data.checkout,
    )


@github_router.post(
    "/{session_id}/checkout",
    summary="切换分支",
    operation_id="checkout_branch"
)
async def checkout_branch(
    session_id: str = Path(..., description="Session ID"),
    data: CheckoutBranchRequest = Body(...),
):
    """切换分支"""
    return await github_service.checkout_branch(
        session_id=session_id,
        branch_name=data.branch_name,
    )


# ===================
# Pull Request Routes
# ===================

@github_router.post(
    "/{session_id}/pull-request",
    summary="创建Pull Request",
    operation_id="create_pull_request"
)
async def create_pull_request(
    session_id: str = Path(..., description="Session ID"),
    data: CreatePRRequest = Body(...),
):
    """创建Pull Request"""
    return await github_service.create_pull_request(
        session_id=session_id,
        title=data.title,
        body=data.body,
        head_branch=data.head_branch,
        base_branch=data.base_branch,
    )
