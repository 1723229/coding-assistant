"""
Business Exception Classes - Base Exception Definitions

Contains all business logic related exception types.
"""

from typing import Optional, Any


class BusinessException(Exception):
    """
    Business Logic Exception
    
    Used to handle exceptions in business logic.
    """

    def __init__(self, message: str, code: int = 400, data: Any = None):
        self.message = message
        self.code = code
        self.data = data
        super().__init__(self.message)


class DatabaseException(Exception):
    """
    Database Exception
    
    Used to handle database operation related exceptions.
    """

    def __init__(self, message: str, code: int = 500, operation: Optional[str] = None):
        self.message = message
        self.code = code
        self.operation = operation
        super().__init__(self.message)


class ValidationException(Exception):
    """
    Data Validation Exception
    
    Used to handle data validation related exceptions.
    """

    def __init__(self, errors: Any, code: int = 422, message: str = "Validation failed"):
        self.errors = errors
        self.code = code
        self.message = message
        super().__init__(self.message)


class NotFoundError(BusinessException):
    """
    Resource Not Found Exception
    
    Used when a requested resource is not found.
    """

    def __init__(self, message: str = "Resource not found", resource_type: Optional[str] = None, resource_id: Optional[str] = None):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(message=message, code=404)


class UnauthorizedError(BusinessException):
    """
    Unauthorized Access Exception
    
    Used when authentication is required but not provided or invalid.
    """

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message=message, code=401)


class ForbiddenError(BusinessException):
    """
    Forbidden Access Exception
    
    Used when the user doesn't have permission to access the resource.
    """

    def __init__(self, message: str = "Forbidden"):
        super().__init__(message=message, code=403)


