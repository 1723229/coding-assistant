"""
Module Schemas

Pydantic models for Module validation and serialization
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.db.models.module import ModuleType


class ModuleBase(BaseModel):
    """Module base schema"""
    project_id: int = Field(..., description="所属项目ID")
    parent_id: Optional[int] = Field(None, description="父节点ID，空则为根节点")
    type: ModuleType = Field(..., description="模块类型：NODE-功能节点 POINT-功能点")
    name: str = Field(..., max_length=255, description="模块名称")
    code: str = Field(..., max_length=64, description="模块代码，在Project内唯一")
    url: Optional[str] = Field(None, max_length=512, description="可访问的链接（NODE类型与子节点共享）")
    require_content: Optional[str] = Field(None, description="功能需求描述")
    # preview_url: Optional[str] = Field(None, max_length=512, description="预览页面，前端不操作")

    # POINT 类型的字段（创建时可选）
    branch: Optional[str] = Field(None, max_length=128, description="Git分支（仅POINT类型）")


class ModuleCreate(ModuleBase):
    """Schema for creating a module"""
    url_parent_id: Optional[int] = Field(None, description="url父节点ID")
    pass


class ModuleUpdate(BaseModel):
    """Schema for updating a module"""
    parent_id: Optional[int] = Field(None, description="父节点ID")
    type: Optional[ModuleType] = Field(None, description="模块类型：NODE-功能节点 POINT-功能点")
    name: Optional[str] = Field(None, max_length=255, description="模块名称")
    code: Optional[str] = Field(None, max_length=64, description="模块代码")
    url: Optional[str] = Field(None, max_length=512, description="菜单")
    require_content: Optional[str] = Field(None, description="功能需求描述")
    # preview_url: Optional[str] = Field(None, max_length=512, description="预览页面，前端不操作")
    branch: Optional[str] = Field(None, max_length=128, description="Git分支（仅POINT类型）")
    container_id: Optional[str] = Field(None, max_length=512, description="容器id")
    latest_commit_id: Optional[str] = Field(None, max_length=64, description="最新commit ID（仅POINT类型）")
    url_parent_id: Optional[int] = Field(None, description="url父节点ID")
    spec_content: Optional[str] = Field(None, description="spec内容")

    model_config = ConfigDict(extra='allow')


class ModuleResponse(ModuleBase):
    """Schema for module response"""
    id: int
    preview_url: Optional[str] = None
    session_id: Optional[str] = None
    workspace_path: Optional[str] = None
    container_id: Optional[str] = None
    is_active: Optional[int] = None
    latest_commit_id: Optional[str] = Field(None, description="最新的commit ID")
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    create_by: Optional[str] = None
    update_by: Optional[str] = None
    spec_content: Optional[str] = None
    url_id: Optional[int] = None

    class Config:
        from_attributes = True


class ModuleTreeResponse(ModuleResponse):
    """Schema for module tree response with children"""
    children: list["ModuleTreeResponse"] = []

    class Config:
        from_attributes = True
