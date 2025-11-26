"""
Message model definition

Chat message model for storing conversation history.
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class Message(Base):
    """
    Chat message model
    
    Stores individual messages in a chat session.
    """
    __tablename__ = "messages"
    __table_args__ = {'comment': 'Chat messages table'}
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True, comment="Message ID")
    
    # Session reference
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False, index=True, comment="Session ID")
    
    # Message content
    role = Column(String(20), nullable=False, comment="Message role: user, assistant, system")
    content = Column(Text, nullable=False, comment="Message content")
    created_at = Column(DateTime, default=datetime.utcnow, comment="Creation time")
    
    # Tool use tracking
    tool_name = Column(String(100), nullable=True, comment="Tool name if tool was used")
    tool_input = Column(Text, nullable=True, comment="Tool input JSON")
    tool_result = Column(Text, nullable=True, comment="Tool execution result")
    
    # Relationships
    session = relationship("Session", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, role='{self.role}', session_id='{self.session_id}')>"
    
    def to_dict(self, exclude_fields=None):
        """
        Convert to dictionary
        
        Args:
            exclude_fields: List of fields to exclude
            
        Returns:
            Dictionary format of message data
        """
        exclude_fields = exclude_fields or []
        data = {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "tool_result": self.tool_result,
        }
        for field in exclude_fields:
            data.pop(field, None)
        return data
    
    def is_user_message(self) -> bool:
        """Check if this is a user message"""
        return self.role == "user"
    
    def is_assistant_message(self) -> bool:
        """Check if this is an assistant message"""
        return self.role == "assistant"
    
    def is_system_message(self) -> bool:
        """Check if this is a system message"""
        return self.role == "system"
    
    def has_tool_use(self) -> bool:
        """Check if this message involves tool use"""
        return self.tool_name is not None


