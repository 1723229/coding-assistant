"""
Workspace service implementation

工作空间管理相关的业务逻辑层
"""

import os
import logging
from pathlib import Path
from typing import Optional
from fastapi import Query

from app.config import get_settings
from app.config.logging_config import log_print
from app.utils.model.response_model import BaseResponse, ListResponse
from app.db.repository import SessionRepository

logger = logging.getLogger(__name__)
settings = get_settings()


class WorkspaceService:
    """
    工作空间服务类
    
    提供工作空间文件操作相关的业务逻辑
    """
    
    def __init__(self):
        self.session_repo = SessionRepository()
    
    def _get_safe_path(self, workspace_path: str, relative_path: str) -> Optional[Path]:
        """
        安全地获取文件路径，防止路径遍历攻击
        
        Args:
            workspace_path: 工作空间根路径
            relative_path: 相对路径
            
        Returns:
            安全的完整路径，如果路径不安全则返回None
        """
        workspace = Path(workspace_path).resolve()
        target = (workspace / relative_path).resolve()
        
        # 确保目标路径在工作空间内
        try:
            target.relative_to(workspace)
            return target
        except ValueError:
            return None
    
    @log_print
    async def list_files(
        self,
        session_id: str,
        path: str = Query("", description="Relative path in workspace"),
    ):
        """列出工作空间目录下的文件"""
        try:
            session = await self.session_repo.get_session_by_id(session_id)
            if not session or not session.workspace_path:
                return BaseResponse.not_found(message=f"会话 '{session_id}' 不存在或无工作空间")
            
            workspace_path = session.workspace_path
            target_path = self._get_safe_path(workspace_path, path)
            
            if not target_path:
                return BaseResponse.business_error(message="路径不安全，禁止访问")
            
            if not target_path.exists():
                return BaseResponse.not_found(message=f"路径 '{path}' 不存在")
            
            if not target_path.is_dir():
                return BaseResponse.business_error(message=f"路径 '{path}' 不是目录")
            
            # 列出目录内容
            items = []
            for item in sorted(target_path.iterdir()):
                # 跳过隐藏文件
                if item.name.startswith('.'):
                    continue

                # 构建相对路径
                relative_item_path = str(Path(path) / item.name) if path else item.name

                items.append({
                    "name": item.name,
                    "path": relative_item_path,
                    "is_directory": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else None,
                })
            
            return ListResponse.success(items=items, total=len(items))
            
        except PermissionError:
            return BaseResponse.business_error(message="权限不足，无法访问该路径")
        except Exception as e:
            return BaseResponse.error(message=f"列出文件失败: {str(e)}")
    
    @log_print
    async def read_file(
        self,
        session_id: str,
        path: str = Query(..., description="Relative path to file"),
    ):
        """读取工作空间中的文件内容"""
        try:
            session = await self.session_repo.get_session_by_id(session_id)
            if not session or not session.workspace_path:
                return BaseResponse.not_found(message=f"会话 '{session_id}' 不存在或无工作空间")
            
            workspace_path = session.workspace_path
            file_path = self._get_safe_path(workspace_path, path)
            
            if not file_path:
                return BaseResponse.business_error(message="路径不安全，禁止访问")
            
            if not file_path.exists():
                return BaseResponse.not_found(message=f"文件 '{path}' 不存在")
            
            if not file_path.is_file():
                return BaseResponse.business_error(message=f"路径 '{path}' 不是文件")
            
            # 检查文件大小
            file_size = file_path.stat().st_size
            max_size = 10 * 1024 * 1024  # 10MB
            if file_size > max_size:
                return BaseResponse.business_error(message=f"文件过大 ({file_size} bytes)，最大支持 {max_size} bytes")
            
            # 读取文件内容
            try:
                content = file_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                return BaseResponse.business_error(message="文件不是有效的文本文件")
            
            return BaseResponse.success(
                data={
                    "path": path,
                    "content": content,
                    "size": file_size,
                },
                message="读取文件成功"
            )
            
        except PermissionError:
            return BaseResponse.business_error(message="权限不足，无法读取该文件")
        except Exception as e:
            return BaseResponse.error(message=f"读取文件失败: {str(e)}")
    
    @log_print
    async def write_file(
        self,
        session_id: str,
        path: str,
        content: str,
    ):
        """写入文件内容到工作空间"""
        try:
            session = await self.session_repo.get_session_by_id(session_id)
            if not session or not session.workspace_path:
                return BaseResponse.not_found(message=f"会话 '{session_id}' 不存在或无工作空间")
            
            workspace_path = session.workspace_path
            file_path = self._get_safe_path(workspace_path, path)
            
            if not file_path:
                return BaseResponse.business_error(message="路径不安全，禁止访问")
            
            # 确保父目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            file_path.write_text(content, encoding='utf-8')
            
            return BaseResponse.success(
                data={
                    "path": path,
                    "size": len(content.encode('utf-8')),
                },
                message="写入文件成功"
            )
            
        except PermissionError:
            return BaseResponse.business_error(message="权限不足，无法写入该文件")
        except Exception as e:
            return BaseResponse.error(message=f"写入文件失败: {str(e)}")
    
    @log_print
    async def delete_file(
        self,
        session_id: str,
        path: str = Query(..., description="Relative path to file"),
    ):
        """删除工作空间中的文件"""
        try:
            session = await self.session_repo.get_session_by_id(session_id)
            if not session or not session.workspace_path:
                return BaseResponse.not_found(message=f"会话 '{session_id}' 不存在或无工作空间")
            
            workspace_path = session.workspace_path
            file_path = self._get_safe_path(workspace_path, path)
            
            if not file_path:
                return BaseResponse.business_error(message="路径不安全，禁止访问")
            
            if not file_path.exists():
                return BaseResponse.not_found(message=f"文件 '{path}' 不存在")
            
            if file_path.is_dir():
                return BaseResponse.business_error(message="不能删除目录，请使用专用接口")
            
            # 删除文件
            file_path.unlink()
            
            return BaseResponse.success(
                data={"path": path},
                message="删除文件成功"
            )
            
        except PermissionError:
            return BaseResponse.business_error(message="权限不足，无法删除该文件")
        except Exception as e:
            return BaseResponse.error(message=f"删除文件失败: {str(e)}")

