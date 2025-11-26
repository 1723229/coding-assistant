"""
Session service implementation

会话管理相关的业务逻辑层
"""

import uuid
import logging
from typing import Optional
from fastapi import Query

from app.db.schemas import SessionCreate, SessionUpdate, SessionResponse, MessageResponse
from app.db.repository import SessionRepository, MessageRepository, GitHubTokenRepository
from app.config import get_settings
from app.config.logging_config import log_print
from app.utils.model.response_model import BaseResponse, ListResponse

logger = logging.getLogger(__name__)
settings = get_settings()


class SessionService:
    """
    会话服务类
    
    提供会话相关的所有业务逻辑操作
    """
    
    def __init__(self):
        self.session_repo = SessionRepository()
        self.message_repo = MessageRepository()
        self.token_repo = GitHubTokenRepository()
    
    def _convert_session_to_dict(self, session) -> dict:
        """将会话模型转换为字典"""
        if not session:
            return None
        return SessionResponse(
            id=session.id,
            name=session.name,
            created_at=session.created_at.isoformat() if session.created_at else None,
            updated_at=session.updated_at.isoformat() if session.updated_at else None,
            is_active=session.is_active,
            workspace_path=session.workspace_path,
            container_id=session.container_id,
            github_repo_url=session.github_repo_url,
            github_branch=session.github_branch,
        ).model_dump()
    
    def _convert_message_to_dict(self, message) -> dict:
        """将消息模型转换为字典"""
        if not message:
            return None
        return MessageResponse(
            id=message.id,
            session_id=message.session_id,
            role=message.role,
            content=message.content,
            created_at=message.created_at.isoformat() if message.created_at else None,
            tool_name=message.tool_name,
        ).model_dump()
    
    @log_print
    async def list_sessions(
        self,
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(50, ge=1, le=100, description="Maximum number of records"),
    ):
        """获取会话列表（分页）"""
        try:
            sessions = await self.session_repo.get_active_sessions(skip=skip, limit=limit)
            items = [self._convert_session_to_dict(s) for s in sessions]
            return ListResponse.success(items=items, total=len(items))
        except Exception as e:
            return BaseResponse.error(message=f"获取会话列表失败: {str(e)}")
    
    @log_print
    async def create_session(self, data: SessionCreate):
        """创建新会话"""
        from app.services import docker_service
        from app.services.github_service import GitHubService
        
        try:
            session_id = str(uuid.uuid4())
            workspace_path = str(settings.workspace_base_path / session_id)
            
            # 创建会话记录
            session = await self.session_repo.create_session(
                session_id=session_id,
                name=data.name or "New Session",
                workspace_path=workspace_path,
                github_repo_url=data.github_repo_url,
                github_branch=data.github_branch or "main",
            )
            
            # 尝试创建Docker容器
            try:
                container_info = await docker_service.create_workspace(
                    session_id=session_id,
                    workspace_path=workspace_path
                )
                await self.session_repo.update_session(session_id, container_id=container_info.id)
            except Exception as e:
                logger.warning(f"Failed to create container: {e}")
            
            # 如果提供了GitHub仓库，尝试克隆
            if data.github_repo_url:
                try:
                    token_record = await self.token_repo.get_latest_token(platform="GitHub")
                    service = GitHubService(token=token_record.token if token_record else None)
                    await service.clone_repo(
                        repo_url=data.github_repo_url,
                        target_path=workspace_path,
                        branch=data.github_branch,
                    )
                except Exception as e:
                    logger.warning(f"Failed to clone repo: {e}")
            
            # 刷新会话数据
            session = await self.session_repo.get_session_by_id(session_id)
            session_dict = self._convert_session_to_dict(session)
            
            return BaseResponse.created(data=session_dict, message="会话创建成功")
            
        except Exception as e:
            return BaseResponse.error(message=f"创建会话失败: {str(e)}")
    
    @log_print
    async def get_session(self, session_id: str):
        """根据ID获取会话"""
        try:
            session = await self.session_repo.get_session_by_id(session_id)
            if not session:
                return BaseResponse.not_found(message=f"会话 '{session_id}' 不存在")
            
            session_dict = self._convert_session_to_dict(session)
            return BaseResponse.success(data=session_dict, message="获取会话成功")
            
        except Exception as e:
            return BaseResponse.error(message=f"获取会话失败: {str(e)}")
    
    @log_print
    async def update_session(self, session_id: str, data: SessionUpdate):
        """更新会话信息"""
        try:
            # 构建更新数据
            update_data = {}
            if data.name is not None:
                update_data["name"] = data.name
            if data.github_repo_url is not None:
                update_data["github_repo_url"] = data.github_repo_url
            if data.github_branch is not None:
                update_data["github_branch"] = data.github_branch
            
            session = await self.session_repo.update_session(session_id, **update_data)
            if not session:
                return BaseResponse.not_found(message=f"会话 '{session_id}' 不存在")
            
            session_dict = self._convert_session_to_dict(session)
            return BaseResponse.success(data=session_dict, message="会话更新成功")
            
        except Exception as e:
            return BaseResponse.error(message=f"更新会话失败: {str(e)}")
    
    @log_print
    async def delete_session(self, session_id: str):
        """删除会话（软删除）"""
        try:
            success = await self.session_repo.soft_delete_session(session_id)
            if not success:
                return BaseResponse.not_found(message=f"会话 '{session_id}' 不存在")
            
            return BaseResponse.success(
                data={"status": "deleted", "session_id": session_id},
                message="会话删除成功"
            )
            
        except Exception as e:
            return BaseResponse.error(message=f"删除会话失败: {str(e)}")
    
    @log_print
    async def get_session_messages(
        self,
        session_id: str,
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, le=500, description="Maximum number of records"),
    ):
        """获取会话消息列表"""
        try:
            messages = await self.message_repo.get_session_messages(
                session_id=session_id,
                skip=skip,
                limit=limit,
            )
            
            items = [self._convert_message_to_dict(m) for m in messages]
            return ListResponse.success(items=items, total=len(items))
            
        except Exception as e:
            return BaseResponse.error(message=f"获取消息列表失败: {str(e)}")

