"""
Unified Response Model

Provides standardized API response format for all endpoints.
"""

from typing import Any, List, Optional, Union
from pydantic import BaseModel, Field
from .response_code import ResponseCode


def default_data():
    """Default data factory for empty responses"""
    return ""


class BaseResponse(BaseModel):
    """Base response model for all API endpoints"""
    
    code: int = Field(200, description="API status code")
    message: str = Field("success", description="API status message")
    data: Optional[Union[Any, None]] = Field(default_factory=default_data, description="API data")

    model_config = {
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "code": 200,
                "message": "success",
                "data": None
            }
        }
    }

    @classmethod
    def success(cls, data: Optional[Any] = "", message: str = None):
        """
        Create success response
        
        Args:
            data: Response data
            message: Custom success message
            
        Returns:
            BaseResponse with success status
        """
        if message is None:
            message = ResponseCode.get_message(ResponseCode.SUCCESS)
        return cls(code=ResponseCode.SUCCESS, message=message, data=data)

    @classmethod
    def error(cls, data: Optional[Any] = "", message: str = None, code: int = None):
        """
        Create error response
        
        Args:
            data: Response data
            message: Custom error message
            code: Error status code
            
        Returns:
            BaseResponse with error status
        """
        if code is None:
            code = ResponseCode.INTERNAL_SERVER_ERROR
        if message is None:
            message = ResponseCode.get_message(code)
        return cls(code=code, message=message, data=data)

    @classmethod
    def created(cls, data: Optional[Any] = "", message: str = None):
        """Create response for resource creation"""
        if message is None:
            message = ResponseCode.get_message(ResponseCode.CREATED)
        return cls(code=ResponseCode.CREATED, message=message, data=data)

    @classmethod
    def not_found(cls, data: Optional[Any] = "", message: str = None):
        """Create response for resource not found"""
        if message is None:
            message = ResponseCode.get_message(ResponseCode.NOT_FOUND)
        return cls(code=ResponseCode.NOT_FOUND, message=message, data=data)

    @classmethod
    def unauthorized(cls, data: Optional[Any] = "", message: str = None):
        """Create response for unauthorized access"""
        if message is None:
            message = ResponseCode.get_message(ResponseCode.UNAUTHORIZED)
        return cls(code=ResponseCode.UNAUTHORIZED, message=message, data=data)

    @classmethod
    def forbidden(cls, data: Optional[Any] = "", message: str = None):
        """Create response for forbidden access"""
        if message is None:
            message = ResponseCode.get_message(ResponseCode.FORBIDDEN)
        return cls(code=ResponseCode.FORBIDDEN, message=message, data=data)

    @classmethod
    def bad_request(cls, data: Optional[Any] = "", message: str = None):
        """Create response for bad request"""
        if message is None:
            message = ResponseCode.get_message(ResponseCode.BAD_REQUEST)
        return cls(code=ResponseCode.BAD_REQUEST, message=message, data=data)

    @classmethod
    def validation_error(cls, data: Optional[Any] = "", message: str = None):
        """Create response for validation error"""
        if message is None:
            message = ResponseCode.get_message(ResponseCode.VALIDATION_ERROR)
        return cls(code=ResponseCode.VALIDATION_ERROR, message=message, data=data)

    @classmethod
    def business_error(cls, data: Optional[Any] = "", message: str = None):
        """Create response for business logic error"""
        if message is None:
            message = ResponseCode.get_message(ResponseCode.BUSINESS_ERROR)
        return cls(code=ResponseCode.BUSINESS_ERROR, message=message, data=data)


class ListResponse(BaseResponse):
    """Response model for list endpoints with pagination"""
    
    @classmethod
    def success(cls, items: List[Any], total: int = None, page: int = None, size: int = None, message: str = None):
        """
        Create success response for list data
        
        Args:
            items: List of items
            total: Total count
            page: Current page
            size: Page size
            message: Custom message
            
        Returns:
            BaseResponse with list data
        """
        if message is None:
            message = ResponseCode.get_message(ResponseCode.SUCCESS)
        
        data = {
            "items": items,
            "total": total if total is not None else len(items)
        }
        
        if page is not None:
            data["page"] = page
        if size is not None:
            data["size"] = size
            
        return cls(code=ResponseCode.SUCCESS, message=message, data=data)


