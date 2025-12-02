"""
Version Schemas

Pydantic models for Version validation and serialization
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class VersionBase(BaseModel):
    """Version base schema"""
    code: str = Field(..., max_length=64, description="版本编号")
    module_id: int = Field(..., description="所属模块ID")
    msg: Optional[str] = Field(None, max_length=512, description="提交信息")
    commit: str = Field(..., max_length=64, description="Git commit ID")

    @field_validator("commit")
    @classmethod
    def validate_commit(cls, v: str) -> str:
        """Validate commit hash format"""
        if not v or len(v) < 7:
            raise ValueError("Commit hash must be at least 7 characters")
        if not all(c in "0123456789abcdefABCDEF" for c in v):
            raise ValueError("Commit hash must be a valid hex string")
        return v.lower()

    @field_validator("msg")
    @classmethod
    def format_msg(cls, v: Optional[str]) -> Optional[str]:
        """Format commit message with prefix if not already present"""
        if v and not v.startswith("[SpecCoding Auto Commit]"):
            return f"[SpecCoding Auto Commit] - {v}"
        return v


class VersionCreate(VersionBase):
    """Schema for creating a version"""
    pass


class VersionUpdate(BaseModel):
    """Schema for updating a version"""
    code: Optional[str] = Field(None, max_length=64, description="版本编号")
    msg: Optional[str] = Field(None, max_length=512, description="提交信息")
    commit: Optional[str] = Field(None, max_length=64, description="Git commit ID")

    @field_validator("commit")
    @classmethod
    def validate_commit(cls, v: Optional[str]) -> Optional[str]:
        """Validate commit hash format"""
        if v is not None:
            if len(v) < 7:
                raise ValueError("Commit hash must be at least 7 characters")
            if not all(c in "0123456789abcdefABCDEF" for c in v):
                raise ValueError("Commit hash must be a valid hex string")
            return v.lower()
        return v

    @field_validator("msg")
    @classmethod
    def format_msg(cls, v: Optional[str]) -> Optional[str]:
        """Format commit message with prefix if not already present"""
        if v and not v.startswith("[SpecCoding Auto Commit]"):
            return f"[SpecCoding Auto Commit] - {v}"
        return v


class VersionResponse(VersionBase):
    """Schema for version response"""
    id: int
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    create_by: Optional[str] = None
    update_by: Optional[str] = None

    class Config:
        from_attributes = True
