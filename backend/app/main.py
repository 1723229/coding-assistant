"""
FastAPI Application - Main Entry Point

This module provides the main FastAPI application for the Claude Code Web Platform.
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import configuration and components
from app.config import get_settings, ClaudeConfig
from app.db.base import init_db, dispose_db
from app.utils.exceptions import (
    BusinessException,
    DatabaseException,
    ValidationException,
    NotFoundError,
)
from app.services import session_claude_manager

# Import API routers
from app.routers import (
    sessions_router,
    chat_router,
    github_router,
    workspace_router,
)

# Get settings
settings = get_settings()

# Setup Claude environment variables
ClaudeConfig.setup_environment()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI application lifecycle management
    
    Handles startup and shutdown events for:
    - Database initialization
    - Claude session manager cleanup task
    """
    # Startup
    logger.info("=" * 80)
    logger.info("🚀 Starting Claude Code Web Platform...")
    logger.info("=" * 80)
    
    # Initialize database
    try:
        await init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        logger.warning("⚠️  Application will start but database operations may fail")
    
    # Start Claude session cleanup task
    try:
        await session_claude_manager.start_cleanup_task()
        logger.info("✅ Claude session manager started")
    except Exception as e:
        logger.error(f"❌ Claude session manager failed to start: {e}")
    
    logger.info("✅ Application startup complete")
    logger.info(f"📍 Server URL: http://{settings.host}:{settings.port}")
    logger.info(f"📚 Documentation: http://{settings.host}:{settings.port}/docs")
    logger.info("=" * 80)
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down application...")
    
    # Stop Claude session cleanup task
    try:
        await session_claude_manager.stop_cleanup_task()
        await session_claude_manager.close_all()
        logger.info("✅ Claude session manager stopped")
    except Exception as e:
        logger.error(f"❌ Error stopping Claude session manager: {e}")
    
    # Close database connections
    try:
        await dispose_db()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"❌ Error closing database: {e}")
    
    logger.info("👋 Application shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application
    
    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Web-based Claude Code programming platform with multi-turn conversation support",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Add CORS middleware (must be first)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Process-Time"],
    )

    # Register global exception handlers
    @app.exception_handler(BusinessException)
    async def business_exception_handler(request: Request, exc: BusinessException):
        """Handle business logic exceptions"""
        return JSONResponse(
            status_code=exc.code,
            content={
                "code": exc.code,
                "message": exc.message,
                "data": exc.data if hasattr(exc, 'data') else ""
            }
        )

    @app.exception_handler(NotFoundError)
    async def not_found_exception_handler(request: Request, exc: NotFoundError):
        """Handle not found exceptions"""
        return JSONResponse(
            status_code=404,
            content={
                "code": 404,
                "message": exc.message,
                "data": {
                    "resource_type": exc.resource_type,
                    "resource_id": exc.resource_id,
                } if exc.resource_type else ""
            }
        )

    @app.exception_handler(DatabaseException)
    async def database_exception_handler(request: Request, exc: DatabaseException):
        """Handle database exceptions"""
        logger.error(f"Database error: {exc.message}", exc_info=True)
        return JSONResponse(
            status_code=exc.code,
            content={
                "code": exc.code,
                "message": "Database operation failed",
                "data": ""
            }
        )

    @app.exception_handler(ValidationException)
    async def validation_exception_handler(request: Request, exc: ValidationException):
        """Handle validation exceptions"""
        return JSONResponse(
            status_code=exc.code,
            content={
                "code": exc.code,
                "message": exc.message,
                "data": exc.errors
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions"""
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "Internal server error",
                "data": ""
            }
        )

    # Health check endpoint
    @app.get("/", tags=["system"])
    async def root():
        """Root endpoint - health check"""
        return {
            "status": "ok",
            "app": settings.app_name,
            "version": "1.0.0",
        }

    @app.get("/health", tags=["system"])
    async def health_check():
        """Detailed health check endpoint"""
        return {
            "status": "healthy",
            "version": "1.0.0",
            "services": {
                "database": "connected",
                "claude_sdk": "configured",
            }
        }

    @app.get("/api/health", tags=["system"])
    async def api_health_check():
        """API health check endpoint"""
        return {
            "status": "healthy",
            "version": "1.0.0",
            "services": {
                "database": "connected",
                "claude_sdk": "configured",
            }
        }

    # Include routers
    app.include_router(sessions_router, prefix="/api/sessions", tags=["sessions"])
    app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
    app.include_router(github_router, prefix="/api/github", tags=["github"])
    app.include_router(workspace_router, prefix="/api/workspace", tags=["workspace"])

    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    logger.info("=" * 80)
    logger.info("🚀 Starting Claude Code Web Platform Server...")
    logger.info("=" * 80)
    logger.info(f"  - Server URL: http://{settings.host}:{settings.port}")
    logger.info(f"  - Documentation: http://{settings.host}:{settings.port}/docs")
    logger.info(f"  - Health Check: http://{settings.host}:{settings.port}/health")
    logger.info("=" * 80)
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
