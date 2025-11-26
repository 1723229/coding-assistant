"""
Database base configuration and models

Provides the base configuration for SQLAlchemy engine, session management,
and base model classes.
"""

import json
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.config import DatabaseConfig

# Build database connection URL
DATABASE_URL = DatabaseConfig.get_database_url()

# Create asynchronous database engine
async_engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool,  # Prevents event loop binding issues in streaming contexts
    echo=False,
    json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
)

# Create asynchronous session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Declarative base class
Base: DeclarativeMeta = declarative_base()


async def init_db():
    """Initialize database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_db():
    """Dispose database engine."""
    await async_engine.dispose()

