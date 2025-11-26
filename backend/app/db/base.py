"""
Database base configuration and models

Provides the base configuration for SQLAlchemy engine, session management,
and base model classes following employee-platform architecture pattern.
"""

import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, DateTime, String
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool, NullPool

from app.config.settings import DatabaseConfig

# Build database connection URLs
DATABASE_URL = DatabaseConfig.get_database_url()
ASYNC_DATABASE_URL = DatabaseConfig.get_async_database_url()

# Create synchronous database engine (for backward compatibility)
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_pre_ping=True,
    pool_recycle=DatabaseConfig.POOL_RECYCLE,
    pool_size=DatabaseConfig.POOL_SIZE,
    max_overflow=DatabaseConfig.MAX_OVERFLOW,
    echo=False,
    connect_args={
        "connect_timeout": DatabaseConfig.CONNECT_TIMEOUT,
        "read_timeout": DatabaseConfig.READ_TIMEOUT,
        "write_timeout": DatabaseConfig.WRITE_TIMEOUT,
        "charset": DatabaseConfig.CHARSET,
    },
    json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
)

# Create asynchronous database engine
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    poolclass=NullPool,  # Prevents event loop binding issues in streaming contexts
    echo=False,
)

# Create synchronous session factory (for backward compatibility)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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


class BaseModel:
    """
    Base model - provides common fields and methods
    """

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="Primary Key ID")
    create_time = Column(DateTime, default=datetime.now, comment="Creation Time")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="Update Time")
    create_by = Column(String(64), default=None, comment="Created By")
    update_by = Column(String(64), default=None, comment="Updated By")

    def to_dict(self, exclude_fields=None):
        """
        Convert model instance to dictionary

        Args:
            exclude_fields: List of field names to exclude

        Returns:
            Dictionary representation of the model
        """
        exclude_fields = exclude_fields or []
        return {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
            if c.name not in exclude_fields
        }


async def init_db():
    """Initialize database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_db():
    """Dispose database engine."""
    await async_engine.dispose()
