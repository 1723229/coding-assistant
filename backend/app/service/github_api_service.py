"""
GitHub API service implementation

GitHub相关API的业务逻辑层
"""

import logging
from typing import Optional
from dataclasses import asdict
from fastapi import Query

from app.config.logging_config import log_print
from app.utils.model.response_model import BaseResponse, ListResponse
from app.db.repository import SessionRepository, GitHubTokenRepository
from app.db.schemas import GitHubTokenCreate
from app.core.github_service import (
    GitHubService, 
    GitOperationError, 
    GitHubAPIError
)

logger = logging.getLogger(__name__)


class GitHubApiService:
    """
    GitHub API服务类
    
    提供GitHub相关API的所有业务逻辑操作
    """
    
    def __init__(self):
        self.session_repo = SessionRepository()
        self.token_repo = GitHubTokenRepository()
    
    async def _get_github_service(self) -> GitHubService:
        """获取配置了token的GitHubService实例"""
        token_record = await self.token_repo.get_latest_token(platform="GitHub")
        return GitHubService(token=token_record.token if token_record else None)
    
    # ===================
    # Token Management
    # ===================
    
    @log_print
    async def list_tokens(self):
        """获取所有GitHub tokens"""
        try:
            tokens = await self.token_repo.get_active_tokens()
            items = [
                {
                    "id": t.id,
                    "platform": t.platform,
                    "domain": t.domain,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in tokens
            ]
            return ListResponse.success(items=items, total=len(items))
        except Exception as e:
            return BaseResponse.error(message=f"获取Token列表失败: {str(e)}")
    
    @log_print
    async def create_token(self, data: GitHubTokenCreate):
        """创建新的GitHub token"""
        import uuid
        try:
            token_id = str(uuid.uuid4())
            token = await self.token_repo.create_token(
                token_id=token_id,
                token=data.token,
                platform=data.platform or "GitHub",
                domain=data.domain or "github.com",
            )
            return BaseResponse.created(
                data={
                    "id": token.id,
                    "platform": token.platform,
                    "domain": token.domain,
                    "created_at": token.created_at.isoformat() if token.created_at else None,
                },
                message="Token创建成功"
            )
        except Exception as e:
            return BaseResponse.error(message=f"创建Token失败: {str(e)}")
    
    @log_print
    async def delete_token(self, token_id: int):
        """删除GitHub token"""
        try:
            success = await self.token_repo.delete_token(token_id)
            if not success:
                return BaseResponse.not_found(message=f"Token ID '{token_id}' 不存在")
            return BaseResponse.success(
                data={"id": token_id},
                message="Token删除成功"
            )
        except Exception as e:
            return BaseResponse.error(message=f"删除Token失败: {str(e)}")
    
    # ===================
    # Repository Operations
    # ===================
    
    @log_print
    async def list_repos(
        self,
        query: Optional[str] = Query(None, description="Search query"),
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(30, ge=1, le=100, description="Items per page"),
    ):
        """获取用户的GitHub仓库列表"""
        try:
            service = await self._get_github_service()
            repos = await service.list_user_repos(query=query, page=page, per_page=per_page)
            items = [asdict(r) for r in repos]
            return ListResponse.success(items=items, total=len(items))
        except GitHubAPIError as e:
            return BaseResponse.business_error(message=f"GitHub API错误: {str(e)}")
        except Exception as e:
            return BaseResponse.error(message=f"获取仓库列表失败: {str(e)}")
    
    @log_print
    async def get_repo_info(self, repo_url: str):
        """获取仓库信息"""
        try:
            service = await self._get_github_service()
            repo_info = await service.get_repo_info(repo_url)
            return BaseResponse.success(data=asdict(repo_info), message="获取仓库信息成功")
        except GitHubAPIError as e:
            return BaseResponse.business_error(message=f"GitHub API错误: {str(e)}")
        except Exception as e:
            return BaseResponse.error(message=f"获取仓库信息失败: {str(e)}")
    
    @log_print
    async def clone_repo(
        self,
        session_id: str,
        repo_url: str,
        branch: Optional[str] = None,
    ):
        """克隆仓库到会话工作空间"""
        try:
            session = await self.session_repo.get_session_by_id(session_id)
            if not session:
                return BaseResponse.not_found(message=f"会话 '{session_id}' 不存在")
            
            if not session.workspace_path:
                return BaseResponse.business_error(message="会话没有工作空间路径")
            
            service = await self._get_github_service()
            await service.clone_repo(
                repo_url=repo_url,
                target_path=session.workspace_path,
                branch=branch,
            )
            
            # 更新会话的GitHub信息
            await self.session_repo.update_session(
                session_id,
                github_repo_url=repo_url,
                github_branch=branch or "main",
            )
            
            return BaseResponse.success(
                data={"repo_url": repo_url, "branch": branch or "main"},
                message="仓库克隆成功"
            )
        except GitOperationError as e:
            return BaseResponse.business_error(message=f"Git操作错误: {str(e)}")
        except Exception as e:
            return BaseResponse.error(message=f"克隆仓库失败: {str(e)}")
    
    # ===================
    # Local Git Operations
    # ===================
    
    @log_print
    async def get_local_changes(
        self,
        session_id: str,
        include_diff: bool = Query(False, description="Include diff content"),
    ):
        """获取本地变更"""
        try:
            session = await self.session_repo.get_session_by_id(session_id)
            if not session:
                return BaseResponse.not_found(message=f"会话 '{session_id}' 不存在")
            
            if not session.workspace_path:
                return BaseResponse.business_error(message="会话没有工作空间路径")
            
            service = await self._get_github_service()
            changes = await service.get_local_changes(
                repo_path=session.workspace_path,
                include_diff=include_diff,
            )
            
            items = [asdict(c) for c in changes]
            return ListResponse.success(items=items, total=len(items))
        except GitOperationError as e:
            return BaseResponse.business_error(message=f"Git {e.operation} 失败: {str(e)}")
        except Exception as e:
            return BaseResponse.error(message=f"获取变更失败: {str(e)}")
    
    @log_print
    async def get_file_diff(
        self,
        session_id: str,
        file_path: str = Query(..., description="Path to file"),
    ):
        """获取文件差异"""
        try:
            session = await self.session_repo.get_session_by_id(session_id)
            if not session:
                return BaseResponse.not_found(message=f"会话 '{session_id}' 不存在")
            
            if not session.workspace_path:
                return BaseResponse.business_error(message="会话没有工作空间路径")
            
            service = await self._get_github_service()
            diff = await service.get_file_diff(
                repo_path=session.workspace_path,
                file_path=file_path,
            )
            
            return BaseResponse.success(
                data={"file_path": file_path, "diff": diff},
                message="获取差异成功"
            )
        except GitOperationError as e:
            return BaseResponse.business_error(message=f"Git {e.operation} 失败: {str(e)}")
        except Exception as e:
            return BaseResponse.error(message=f"获取差异失败: {str(e)}")
    
    @log_print
    async def commit_changes(
        self,
        session_id: str,
        message: str,
        files: Optional[list[str]] = None,
    ):
        """提交变更"""
        try:
            session = await self.session_repo.get_session_by_id(session_id)
            if not session:
                return BaseResponse.not_found(message=f"会话 '{session_id}' 不存在")
            
            if not session.workspace_path:
                return BaseResponse.business_error(message="会话没有工作空间路径")
            
            service = await self._get_github_service()
            commit_sha = await service.commit_changes(
                repo_path=session.workspace_path,
                message=message,
                files=files,
            )
            
            return BaseResponse.success(
                data={"commit_sha": commit_sha},
                message="提交成功"
            )
        except GitOperationError as e:
            return BaseResponse.business_error(message=f"Git {e.operation} 失败: {str(e)}")
        except Exception as e:
            return BaseResponse.error(message=f"提交失败: {str(e)}")
    
    @log_print
    async def push_changes(
        self,
        session_id: str,
        branch: Optional[str] = None,
    ):
        """推送变更到远程"""
        try:
            session = await self.session_repo.get_session_by_id(session_id)
            if not session:
                return BaseResponse.not_found(message=f"会话 '{session_id}' 不存在")
            
            if not session.workspace_path:
                return BaseResponse.business_error(message="会话没有工作空间路径")
            
            service = await self._get_github_service()
            await service.push_changes(
                repo_path=session.workspace_path,
                branch=branch,
            )
            
            return BaseResponse.success(message="推送成功")
        except GitOperationError as e:
            return BaseResponse.business_error(message=f"Git {e.operation} 失败: {str(e)}")
        except Exception as e:
            return BaseResponse.error(message=f"推送失败: {str(e)}")
    
    @log_print
    async def pull_changes(self, session_id: str):
        """拉取远程变更"""
        try:
            session = await self.session_repo.get_session_by_id(session_id)
            if not session:
                return BaseResponse.not_found(message=f"会话 '{session_id}' 不存在")
            
            if not session.workspace_path:
                return BaseResponse.business_error(message="会话没有工作空间路径")
            
            service = await self._get_github_service()
            await service.pull_changes(repo_path=session.workspace_path)
            
            return BaseResponse.success(message="拉取成功")
        except GitOperationError as e:
            return BaseResponse.business_error(message=f"Git {e.operation} 失败: {str(e)}")
        except Exception as e:
            return BaseResponse.error(message=f"拉取失败: {str(e)}")
    
    # ===================
    # Branch Operations
    # ===================
    
    @log_print
    async def list_branches(self, session_id: str):
        """获取分支列表"""
        try:
            session = await self.session_repo.get_session_by_id(session_id)
            if not session:
                return BaseResponse.not_found(message=f"会话 '{session_id}' 不存在")
            
            if not session.workspace_path:
                return BaseResponse.business_error(message="会话没有工作空间路径")
            
            service = await self._get_github_service()
            branches = await service.list_branches(repo_path=session.workspace_path)
            
            items = [asdict(b) for b in branches]
            return ListResponse.success(items=items, total=len(items))
        except GitOperationError as e:
            return BaseResponse.business_error(message=f"Git {e.operation} 失败: {str(e)}")
        except Exception as e:
            return BaseResponse.error(message=f"获取分支列表失败: {str(e)}")
    
    @log_print
    async def create_branch(
        self,
        session_id: str,
        branch_name: str,
        checkout: bool = True,
    ):
        """创建新分支"""
        try:
            session = await self.session_repo.get_session_by_id(session_id)
            if not session:
                return BaseResponse.not_found(message=f"会话 '{session_id}' 不存在")
            
            if not session.workspace_path:
                return BaseResponse.business_error(message="会话没有工作空间路径")
            
            service = await self._get_github_service()
            await service.create_branch(
                repo_path=session.workspace_path,
                branch_name=branch_name,
                checkout=checkout,
            )
            
            return BaseResponse.created(
                data={"branch_name": branch_name},
                message="分支创建成功"
            )
        except GitOperationError as e:
            return BaseResponse.business_error(message=f"Git {e.operation} 失败: {str(e)}")
        except Exception as e:
            return BaseResponse.error(message=f"创建分支失败: {str(e)}")
    
    @log_print
    async def checkout_branch(
        self,
        session_id: str,
        branch_name: str,
    ):
        """切换分支"""
        try:
            session = await self.session_repo.get_session_by_id(session_id)
            if not session:
                return BaseResponse.not_found(message=f"会话 '{session_id}' 不存在")
            
            if not session.workspace_path:
                return BaseResponse.business_error(message="会话没有工作空间路径")
            
            service = await self._get_github_service()
            await service.checkout_branch(
                repo_path=session.workspace_path,
                branch_name=branch_name,
            )
            
            # 更新会话的分支信息
            await self.session_repo.update_session(
                session_id,
                github_branch=branch_name,
            )
            
            return BaseResponse.success(
                data={"branch_name": branch_name},
                message="切换分支成功"
            )
        except GitOperationError as e:
            return BaseResponse.business_error(message=f"Git {e.operation} 失败: {str(e)}")
        except Exception as e:
            return BaseResponse.error(message=f"切换分支失败: {str(e)}")
    
    # ===================
    # Pull Request Operations
    # ===================
    
    @log_print
    async def create_pull_request(
        self,
        session_id: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: Optional[str] = None,
    ):
        """创建Pull Request"""
        try:
            session = await self.session_repo.get_session_by_id(session_id)
            if not session:
                return BaseResponse.not_found(message=f"会话 '{session_id}' 不存在")
            
            if not session.github_repo_url:
                return BaseResponse.business_error(message="会话没有关联GitHub仓库")
            
            service = await self._get_github_service()
            pr_info = await service.create_pull_request(
                repo_url=session.github_repo_url,
                title=title,
                body=body,
                head_branch=head_branch,
                base_branch=base_branch,
            )
            
            return BaseResponse.created(data=asdict(pr_info), message="Pull Request创建成功")
        except GitHubAPIError as e:
            return BaseResponse.business_error(message=f"GitHub API错误: {str(e)}")
        except Exception as e:
            return BaseResponse.error(message=f"创建Pull Request失败: {str(e)}")

