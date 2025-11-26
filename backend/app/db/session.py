"""
Database session management

Provides session management utilities including context managers,
decorators, and dependency injection for FastAPI.
"""

import logging
from contextlib import asynccontextmanager
from functools import wraps
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from .base import AsyncSessionLocal

logger = logging.getLogger(__name__)


@asynccontextmanager
async def async_session_scope() -> AsyncGenerator[AsyncSession, None]:
    """
    Asynchronous context manager for automatic async Session management
    
    Usage:
        async with async_session_scope() as session:
            # Asynchronous database operations
            result = await session.execute(stmt)
    """
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def async_with_session(f):
    """
    Asynchronous decorator: Automatically handle async database session management
    
    Usage:
        @async_with_session
        async def some_db_function(session, param1, param2):
            # session parameter will be automatically injected
            result = await session.execute(stmt)
            return result.scalars().all()
    """
    @wraps(f)
    async def wrapper(*args, **kwargs):
        async with async_session_scope() as session:
            try:
                # For instance methods, insert session as the second argument (after self)
                if args and hasattr(args[0], '__class__') and hasattr(args[0].__class__, f.__name__):
                    # Instance method: self is first arg, insert session as second
                    new_args = (args[0], session) + args[1:]
                else:
                    # Static/module function: session is first arg
                    new_args = (session,) + args

                result = await f(*new_args, **kwargs)

                # AsyncSession handles expunge differently, objects are already detached
                # after commit with expire_on_commit=False
                await session.commit()
                return result
            except Exception as e:
                await session.rollback()
                logger.error(f"Database operation failed in {f.__name__}: {e}", exc_info=True)
                raise

    return wrapper


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get asynchronous database session - for FastAPI async endpoint dependency injection
    
    Yields:
        Asynchronous database session object
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_async_db_session() -> AsyncSession:
    """
    Directly get asynchronous database session instance
    
    Returns:
        Asynchronous database session object
    """
    return AsyncSessionLocal()


