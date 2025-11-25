"""SQLAlchemy database models."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey, Integer
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Session(Base):
    """Chat session model."""
    
    __tablename__ = "sessions"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False, default="New Session")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Workspace info
    workspace_path = Column(String(512), nullable=True)
    container_id = Column(String(64), nullable=True)
    
    # GitHub binding
    github_repo_url = Column(String(512), nullable=True)
    github_branch = Column(String(255), default="main")
    
    # Relationships
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    """Chat message model."""
    
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Tool use tracking
    tool_name = Column(String(100), nullable=True)
    tool_input = Column(Text, nullable=True)
    tool_result = Column(Text, nullable=True)
    
    # Relationships
    session = relationship("Session", back_populates="messages")


class Repository(Base):
    """GitHub repository binding model."""
    
    __tablename__ = "repositories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(512), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    owner = Column(String(255), nullable=False)
    default_branch = Column(String(255), default="main")
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class GitHubToken(Base):
    """GitHub/GitLab token storage model."""
    
    __tablename__ = "github_tokens"
    
    id = Column(String(36), primary_key=True)
    platform = Column(String(50), nullable=False)  # "GitHub" | "GitLab"
    domain = Column(String(255), nullable=False, default="github.com")
    token = Column(String(512), nullable=False)  # Encrypted storage recommended
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

