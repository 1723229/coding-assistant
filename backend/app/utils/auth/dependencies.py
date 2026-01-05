"""
Authentication Dependencies

FastAPI dependencies for JWT token extraction and validation
"""

from typing import Optional
from fastapi import Header, HTTPException, status
from app.utils.auth.jwt_utils import JWTUtils
import logging

logger = logging.getLogger(__name__)


async def get_current_user_id(
    authorization: Optional[str] = Header(None, description="Bearer token")
) -> Optional[str]:
    """
    Extract user ID from JWT token in Authorization header

    Args:
        authorization: Authorization header value (format: "Bearer <token>")

    Returns:
        User ID extracted from token, or None if no token provided

    Raises:
        HTTPException: If token is invalid or expired
    """
    if not authorization:
        # No token provided - return None (optional authentication)
        return None

    # Remove "Bearer " prefix
    if authorization.startswith("Bearer "):
        token = authorization[7:]  # Remove "Bearer " (7 characters)
    else:
        token = authorization

    # Extract user ID from token
    try:
        user_id = JWTUtils.extract_user_id(token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: could not extract user ID"
            )
        return user_id
    except Exception as e:
        logger.warning(f"Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}"
        )


async def get_optional_user_id(
    authorization: Optional[str] = Header(None, description="Bearer token")
) -> Optional[str]:
    """
    Extract user ID from JWT token (optional - no error if missing)

    Args:
        authorization: Authorization header value (format: "Bearer <token>")

    Returns:
        User ID extracted from token, or None if no token or invalid token
    """
    if not authorization:
        return None

    # Remove "Bearer " prefix
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = authorization

    # Extract user ID from token (silently fail)
    try:
        user_id = JWTUtils.extract_user_id(token)
        return user_id
    except Exception as e:
        logger.debug(f"Optional token validation failed: {e}")
        return None