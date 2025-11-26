"""
Global Exception Handlers

Unified handling of all API exceptions to ensure consistent error response format.
"""

import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.utils.model.response_model import BaseResponse
from app.utils.model.response_code import ResponseCode
from app.utils.exceptions import BusinessException

logger = logging.getLogger(__name__)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle request parameter validation errors
    
    Args:
        request: Request object
        exc: Validation exception
        
    Returns:
        Unified format error response
    """
    logger.warning(f"Validation error on {request.url}: {exc.errors()}")
    
    # Extract detailed error information
    errors = []
    serializable_errors = []

    for error in exc.errors():
        # Prefer ctx error field, fallback to msg
        if "ctx" in error and isinstance(error["ctx"], dict) and "error" in error["ctx"]:
            message = str(error["ctx"]["error"])
        else:
            message = error["msg"]
        errors.append(message)
        
        # Build serializable error details
        serializable_error = {
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"],
        }
        
        # Convert input to string if present
        if "input" in error:
            try:
                serializable_error["input"] = str(error["input"])
            except Exception:
                serializable_error["input"] = "<cannot serialize>"
        
        # Convert ctx to serializable format
        if "ctx" in error:
            try:
                serializable_error["ctx"] = {k: str(v) for k, v in error["ctx"].items()}
            except Exception:
                serializable_error["ctx"] = str(error.get("ctx", ""))
        
        serializable_errors.append(serializable_error)
    
    error_message = "; ".join(errors)
    
    response = BaseResponse.validation_error(
        data={"details": serializable_errors},
        message=error_message
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response.model_dump()
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions
    
    Args:
        request: Request object
        exc: HTTP exception
        
    Returns:
        Unified format error response
    """
    logger.warning(f"HTTP {exc.status_code} on {request.url}: {exc.detail}")
    
    # Create response based on HTTP status code
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        response = BaseResponse.unauthorized(message=exc.detail)
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        response = BaseResponse.forbidden(message=exc.detail)
    elif exc.status_code == status.HTTP_404_NOT_FOUND:
        response = BaseResponse.not_found(message=exc.detail)
    elif exc.status_code == status.HTTP_400_BAD_REQUEST:
        response = BaseResponse.bad_request(message=exc.detail)
    else:
        response = BaseResponse.error(
            message=exc.detail,
            code=exc.status_code
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump()
    )


async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle Starlette HTTP exceptions
    
    Args:
        request: Request object
        exc: Starlette HTTP exception
        
    Returns:
        Unified format error response
    """
    return await http_exception_handler(request, HTTPException(status_code=exc.status_code, detail=exc.detail))


async def business_exception_handler(request: Request, exc: BusinessException) -> JSONResponse:
    """
    Handle business logic exceptions
    
    Args:
        request: Request object
        exc: Business exception
        
    Returns:
        Unified format error response
    """
    logger.warning(f"Business error on {request.url}: {exc.message}")
    
    # BusinessException may not have data attribute
    data = getattr(exc, "data", None)
    
    response = BaseResponse.business_error(
        message=exc.message,
        data=data
    )
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=response.model_dump()
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all uncaught exceptions
    
    Args:
        request: Request object
        exc: Exception
        
    Returns:
        Unified format error response
    """
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    
    # Return detailed error in development, generic error in production
    import os
    is_dev = os.getenv("ENVIRONMENT", "development") == "development"
    
    if is_dev:
        message = f"Internal server error: {str(exc)}"
        data = {
            "error_type": type(exc).__name__,
            "error_message": str(exc)
        }
    else:
        message = "Internal server error, please try again later"
        data = None
    
    response = BaseResponse.error(
        message=message,
        data=data,
        code=ResponseCode.INTERNAL_SERVER_ERROR
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response.model_dump()
    )


def register_exception_handlers(app):
    """
    Register all exception handlers
    
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)
    app.add_exception_handler(BusinessException, business_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("✅ Exception handlers registered")

