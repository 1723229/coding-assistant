"""
Workspace schemas

Pydantic models for workspace file operations.
"""

from typing import Optional
from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    """File information model"""
    name: str = Field(..., description="File name")
    path: str = Field(..., description="Relative path")
    is_directory: bool = Field(..., description="Is directory")
    size: Optional[int] = Field(None, description="File size in bytes")


class FileContent(BaseModel):
    """File content model"""
    path: str = Field(..., description="File path")
    content: str = Field(..., description="File content")


class FileWriteRequest(BaseModel):
    """Request to write file content"""
    content: str = Field(..., description="File content to write")


class WriteFileRequest(BaseModel):
    """Request to write file with path and content"""
    path: str = Field(..., description="File path")
    content: str = Field(..., description="File content")


