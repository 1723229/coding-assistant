"""
Project Schemas

Pydantic models for Project validation and serialization
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class ProjectBase(BaseModel):
    """Project base schema"""
    code: str = Field(..., max_length=64, description="项目代码，英文+数字，不区分大小写")
    name: str = Field(..., max_length=255, description="项目名称")
    codebase: str = Field(..., max_length=512, description="Git仓库地址")
    token: str = Field(..., max_length=512, description="Git认证令牌")
    owner: int = Field(..., description="持有者ID")
    branch: Optional[str] = Field("main", max_length=128, description="Git分支，默认为main")

    @field_validator("code")
    @classmethod
    def code_alphanumeric(cls, v: str) -> str:
        """Validate code is alphanumeric"""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Project code must be alphanumeric (underscores and hyphens allowed)")
        return v.upper()  # Store in uppercase for case-insensitive comparison


class ProjectCreate(ProjectBase):
    """Schema for creating a project"""
    pass


class ProjectUpdate(BaseModel):
    """Schema for updating a project"""
    code: Optional[str] = Field(None, max_length=64, description="项目代码")
    name: Optional[str] = Field(None, max_length=255, description="项目名称")
    codebase: Optional[str] = Field(None, max_length=512, description="Git仓库地址")
    token: Optional[str] = Field(None, max_length=512, description="Git认证令牌")
    owner: Optional[int] = Field(None, description="持有者ID")
    branch: Optional[str] = Field(None, max_length=128, description="Git分支")
    is_active: Optional[int] = Field(None, description="是否激活")

    @field_validator("code")
    @classmethod
    def code_alphanumeric(cls, v: Optional[str]) -> Optional[str]:
        """Validate code is alphanumeric"""
        if v is not None:
            if not v.replace("_", "").replace("-", "").isalnum():
                raise ValueError("Project code must be alphanumeric (underscores and hyphens allowed)")
            return v.upper()
        return v


class ProjectResponse(ProjectBase):
    """Schema for project response"""
    id: int
    session_id: str
    workspace_path: Optional[str] = None
    container_id: Optional[str] = None
    is_active: int = 1
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    create_by: Optional[str] = None
    update_by: Optional[str] = None

    class Config:
        from_attributes = True
