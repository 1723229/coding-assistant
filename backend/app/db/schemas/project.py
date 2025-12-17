"""
Project Schemas

Pydantic models for Project validation and serialization
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class ProjectBase(BaseModel):
    """Project base schema"""
    code: str = Field(..., max_length=512, description="项目代码，不区分大小写")
    name: str = Field(..., max_length=512, description="项目名称")
    codebase: Optional[str]  = Field(None, max_length=512, description="Git仓库地址")
    token: Optional[str]  = Field(None, max_length=512, description="Git认证令牌")
    owner: Optional[str]  = Field(None, description="持有者ID")

    # @field_validator("code")
    # @classmethod
    # def code_alphanumeric(cls, v: str) -> str:
    #     """Validate code is alphanumeric"""
    #     if not v.replace("_", "").replace("-", "").isalnum():
    #         raise ValueError("Project code must be alphanumeric (underscores and hyphens allowed)")
    #     return v.upper()  # Store in uppercase for case-insensitive comparison


class ProjectCreate(ProjectBase):
    """Schema for creating a project"""
    pass


class ProjectUpdate(BaseModel):
    """Schema for updating a project"""
    code: Optional[str] = Field(None, max_length=512, description="项目代码")
    name: Optional[str] = Field(None, max_length=512, description="项目名称")
    codebase: Optional[str] = Field(None, max_length=512, description="Git仓库地址")
    token: Optional[str] = Field(None, max_length=512, description="Git认证令牌")
    owner: Optional[str] = Field(None, description="持有者ID")

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
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    create_by: Optional[str] = None
    update_by: Optional[str] = None

    class Config:
        from_attributes = True
