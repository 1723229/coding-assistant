"""
Exception Classes

Contains all custom exception types for the application.
"""

from .base_exceptions import (
    BusinessException,
    DatabaseException,
    ValidationException,
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
)

from .exception_handlers import (
    register_exception_handlers,
    validation_exception_handler,
    http_exception_handler,
    business_exception_handler,
    general_exception_handler,
)

__all__ = [
    "BusinessException",
    "DatabaseException",
    "ValidationException",
    "NotFoundError",
    "UnauthorizedError",
    "ForbiddenError",
    "register_exception_handlers",
    "validation_exception_handler",
    "http_exception_handler",
    "business_exception_handler",
    "general_exception_handler",
]
