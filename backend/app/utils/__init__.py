"""
Utilities Module

Common utilities, exceptions, and response models.
"""

from .exceptions import (
    BusinessException,
    DatabaseException,
    ValidationException,
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
    register_exception_handlers,
)
from .model import (
    ResponseCode,
    BaseResponse,
    ListResponse,
)

__all__ = [
    # Exceptions
    "BusinessException",
    "DatabaseException",
    "ValidationException",
    "NotFoundError",
    "UnauthorizedError",
    "ForbiddenError",
    "register_exception_handlers",
    # Response models
    "ResponseCode",
    "BaseResponse",
    "ListResponse",
]
