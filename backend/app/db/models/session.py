"""
Session model definition

Chat session model for managing coding assistant sessions.
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.orm import relationship

from app.db.base import Base


class Session(Base):
    """
    Chat session model
    
    Manages coding assistant chat sessions with workspace and GitHub integration.
    """
    __tablename__ = "sessions"
    __table_args__ = {'comment': 'Chat sessions table'}
    
    # Primary key
    id = Column(String(36), primary_key=True, comment="Session UUID")
    
    # Session info
    name = Column(String(255), nullable=False, default="New Session", comment="Session name")
    created_at = Column(DateTime, default=datetime.utcnow, comment="Creation time")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="Last update time")
    is_active = Column(Boolean, default=True, comment="Is session active")
    
    # Workspace info
    workspace_path = Column(String(512), nullable=True, comment="Local workspace path")
    container_id = Column(String(64), nullable=True, comment="Docker container ID")
    
    # GitHub binding
    github_repo_url = Column(String(512), nullable=True, comment="GitHub repository URL")
    github_branch = Column(String(255), default="main", comment="GitHub branch name")
    
    # Relationships
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Session(id='{self.id}', name='{self.name}', is_active={self.is_active})>"
    
    def to_dict(self, exclude_fields=None):
        """
        Convert to dictionary
        
        Args:
            exclude_fields: List of fields to exclude
            
        Returns:
            Dictionary format of session data
        """
        exclude_fields = exclude_fields or []
        data = {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
            "workspace_path": self.workspace_path,
            "container_id": self.container_id,
            "github_repo_url": self.github_repo_url,
            "github_branch": self.github_branch,
        }
        for field in exclude_fields:
            data.pop(field, None)
        return data
    
    def touch(self):
        """Update the updated_at timestamp"""
        self.updated_at = datetime.utcnow()


