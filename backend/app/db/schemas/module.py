"""
Module Schemas

Pydantic models for Module validation and serialization
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.db.models.module import ModuleType


class ModuleBase(BaseModel):
    """Module base schema"""
    project_id: int = Field(..., description="所属项目ID")
    parent_id: Optional[int] = Field(None, description="父节点ID，空则为根节点")
    type: ModuleType = Field(..., description="模块类型：MENU-菜单项 PAGE-页面")
    name: str = Field(..., max_length=255, description="模块名称")
    code: str = Field(..., max_length=64, description="模块代码，在Project内唯一")
    url: Optional[str] = Field(None, max_length=512, description="可访问的链接")
    branch: Optional[str] = Field(None, max_length=128, description="Git分支")


class ModuleCreate(ModuleBase):
    """Schema for creating a module"""
    pass


class ModuleUpdate(BaseModel):
    """Schema for updating a module"""
    parent_id: Optional[int] = Field(None, description="父节点ID")
    type: Optional[ModuleType] = Field(None, description="模块类型")
    name: Optional[str] = Field(None, max_length=255, description="模块名称")
    code: Optional[str] = Field(None, max_length=64, description="模块代码")
    url: Optional[str] = Field(None, max_length=512, description="可访问的链接")
    branch: Optional[str] = Field(None, max_length=128, description="Git分支")


class ModuleResponse(ModuleBase):
    """Schema for module response"""
    id: int
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    create_by: Optional[str] = None
    update_by: Optional[str] = None

    class Config:
        from_attributes = True


class ModuleTreeResponse(ModuleResponse):
    """Schema for module tree response with children"""
    children: list["ModuleTreeResponse"] = []

    class Config:
        from_attributes = True
