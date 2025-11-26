"""
Session schemas

Pydantic models for session-related requests and responses.
"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class SessionCreate(BaseModel):
    """Request model for creating a session"""
    name: Optional[str] = Field("New Session", description="Session name")
    github_repo_url: Optional[str] = Field(None, description="GitHub repository URL")
    github_branch: Optional[str] = Field("main", description="GitHub branch name")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "My Coding Session",
            "github_repo_url": "https://github.com/user/repo",
            "github_branch": "main"
        }
    })


class SessionUpdate(BaseModel):
    """Request model for updating a session"""
    name: Optional[str] = Field(None, description="Session name")
    github_repo_url: Optional[str] = Field(None, description="GitHub repository URL")
    github_branch: Optional[str] = Field(None, description="GitHub branch name")


class SessionResponse(BaseModel):
    """Response model for session"""
    id: str = Field(..., description="Session UUID")
    name: str = Field(..., description="Session name")
    created_at: str = Field(..., description="Creation time (ISO format)")
    updated_at: str = Field(..., description="Last update time (ISO format)")
    is_active: bool = Field(..., description="Is session active")
    workspace_path: Optional[str] = Field(None, description="Local workspace path")
    container_id: Optional[str] = Field(None, description="Docker container ID")
    github_repo_url: Optional[str] = Field(None, description="GitHub repository URL")
    github_branch: Optional[str] = Field(None, description="GitHub branch name")
    
    model_config = ConfigDict(from_attributes=True)


