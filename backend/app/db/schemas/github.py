"""
GitHub schemas

Pydantic models for GitHub-related requests and responses.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class GitHubTokenCreate(BaseModel):
    """Request to create/add a GitHub token"""
    platform: str = Field(..., description="Platform: GitHub or GitLab")
    domain: str = Field("github.com", description="Platform domain")
    token: str = Field(..., description="Access token")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "platform": "GitHub",
            "domain": "github.com",
            "token": "ghp_xxxxxxxxxxxx"
        }
    })


class GitHubTokenResponse(BaseModel):
    """GitHub token response (masked)"""
    id: str = Field(..., description="Token UUID")
    platform: str = Field(..., description="Platform")
    domain: str = Field(..., description="Domain")
    token: str = Field(..., description="Masked token")
    created_at: str = Field(..., description="Creation time")
    is_active: bool = Field(..., description="Is token active")
    
    model_config = ConfigDict(from_attributes=True)


class CloneRepoRequest(BaseModel):
    """Request to clone a repository"""
    repo_url: str = Field(..., description="Repository URL")
    branch: Optional[str] = Field(None, description="Branch to clone")


class CommitRequest(BaseModel):
    """Request to commit changes"""
    message: str = Field(..., description="Commit message")
    files: Optional[List[str]] = Field(None, description="Specific files to commit")


class PushRequest(BaseModel):
    """Request to push changes"""
    remote: str = Field("origin", description="Remote name")
    branch: Optional[str] = Field(None, description="Branch to push")


class CreateBranchRequest(BaseModel):
    """Request to create a branch"""
    branch_name: str = Field(..., description="New branch name")
    checkout: bool = Field(True, description="Checkout after creation")


class CreatePRRequest(BaseModel):
    """Request to create a pull request"""
    title: str = Field(..., description="PR title")
    body: str = Field(..., description="PR description")
    head_branch: str = Field(..., description="Source branch")
    base_branch: Optional[str] = Field(None, description="Target branch")


class CheckoutBranchRequest(BaseModel):
    """Request to checkout a branch"""
    branch_name: str = Field(..., description="Branch name to checkout")


class RepoInfoResponse(BaseModel):
    """Repository information response"""
    name: str = Field(..., description="Repository name")
    owner: str = Field(..., description="Repository owner")
    full_name: str = Field(..., description="Full name (owner/repo)")
    url: str = Field(..., description="Clone URL")
    default_branch: str = Field(..., description="Default branch")
    description: Optional[str] = Field(None, description="Repository description")
    is_private: bool = Field(..., description="Is private repository")


class FileChangeResponse(BaseModel):
    """File change response"""
    path: str = Field(..., description="File path")
    status: str = Field(..., description="Change status")
    diff: Optional[str] = Field(None, description="Diff content")


class PRResponse(BaseModel):
    """Pull request response"""
    number: int = Field(..., description="PR number")
    title: str = Field(..., description="PR title")
    url: str = Field(..., description="PR URL")
    state: str = Field(..., description="PR state")
    head_branch: str = Field(..., description="Source branch")
    base_branch: str = Field(..., description="Target branch")


