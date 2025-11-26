"""
Message schemas

Pydantic models for message-related requests and responses.
"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class MessageCreate(BaseModel):
    """Request model for creating a message"""
    session_id: str = Field(..., description="Session ID")
    role: str = Field(..., description="Message role: user, assistant, system")
    content: str = Field(..., description="Message content")
    tool_name: Optional[str] = Field(None, description="Tool name if tool was used")
    tool_input: Optional[str] = Field(None, description="Tool input JSON")
    tool_result: Optional[str] = Field(None, description="Tool execution result")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "session_id": "123e4567-e89b-12d3-a456-426614174000",
            "role": "user",
            "content": "Hello, Claude!"
        }
    })


class MessageResponse(BaseModel):
    """Response model for message"""
    id: int = Field(..., description="Message ID")
    session_id: str = Field(..., description="Session ID")
    role: str = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    created_at: str = Field(..., description="Creation time (ISO format)")
    tool_name: Optional[str] = Field(None, description="Tool name")
    
    model_config = ConfigDict(from_attributes=True)


