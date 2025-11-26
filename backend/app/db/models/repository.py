"""
Repository model definition

GitHub repository binding model for tracking cloned repositories.
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime

from app.db.base import Base


class Repository(Base):
    """
    GitHub repository binding model
    
    Tracks GitHub repositories that have been cloned/linked.
    """
    __tablename__ = "repositories"
    __table_args__ = {'comment': 'GitHub repositories table'}
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True, comment="Repository ID")
    
    # Repository info
    url = Column(String(512), nullable=False, unique=True, comment="Repository URL")
    name = Column(String(255), nullable=False, comment="Repository name")
    owner = Column(String(255), nullable=False, comment="Repository owner")
    default_branch = Column(String(255), default="main", comment="Default branch")
    
    # Sync info
    last_synced_at = Column(DateTime, nullable=True, comment="Last sync time")
    created_at = Column(DateTime, default=datetime.utcnow, comment="Creation time")
    
    def __repr__(self):
        return f"<Repository(id={self.id}, name='{self.name}', owner='{self.owner}')>"
    
    def to_dict(self, exclude_fields=None):
        """
        Convert to dictionary
        
        Args:
            exclude_fields: List of fields to exclude
            
        Returns:
            Dictionary format of repository data
        """
        exclude_fields = exclude_fields or []
        data = {
            "id": self.id,
            "url": self.url,
            "name": self.name,
            "owner": self.owner,
            "default_branch": self.default_branch,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        for field in exclude_fields:
            data.pop(field, None)
        return data
    
    @property
    def full_name(self) -> str:
        """Get full repository name (owner/name)"""
        return f"{self.owner}/{self.name}"

