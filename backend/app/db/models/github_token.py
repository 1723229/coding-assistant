"""
GitHub Token model definition

GitHub/GitLab token storage model.
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean

from app.db.base import Base


class GitHubToken(Base):
    """
    GitHub/GitLab token storage model
    
    Stores access tokens for GitHub/GitLab integration.
    """
    __tablename__ = "github_tokens"
    __table_args__ = {'comment': 'GitHub/GitLab tokens table'}
    
    # Primary key
    id = Column(String(36), primary_key=True, comment="Token UUID")
    
    # Token info
    platform = Column(String(50), nullable=False, comment="Platform: GitHub or GitLab")
    domain = Column(String(255), nullable=False, default="github.com", comment="Platform domain")
    token = Column(String(512), nullable=False, comment="Access token (encrypted storage recommended)")
    
    # Status
    created_at = Column(DateTime, default=datetime.utcnow, comment="Creation time")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="Last update time")
    is_active = Column(Boolean, default=True, comment="Is token active")
    
    def __repr__(self):
        return f"<GitHubToken(id='{self.id}', platform='{self.platform}', domain='{self.domain}')>"
    
    def to_dict(self, exclude_fields=None, mask_token=True):
        """
        Convert to dictionary
        
        Args:
            exclude_fields: List of fields to exclude
            mask_token: Whether to mask the token value
            
        Returns:
            Dictionary format of token data
        """
        exclude_fields = exclude_fields or []
        
        token_value = self.token
        if mask_token and token_value:
            if len(token_value) <= 8:
                token_value = "****"
            else:
                token_value = f"{token_value[:4]}{'*' * (len(token_value) - 8)}{token_value[-4:]}"
        
        data = {
            "id": self.id,
            "platform": self.platform,
            "domain": self.domain,
            "token": token_value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
        }
        for field in exclude_fields:
            data.pop(field, None)
        return data
    
    def is_github(self) -> bool:
        """Check if this is a GitHub token"""
        return self.platform.lower() == "github"
    
    def is_gitlab(self) -> bool:
        """Check if this is a GitLab token"""
        return self.platform.lower() == "gitlab"


