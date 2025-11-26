#!/usr/bin/env python3
"""
Claude Code Web Platform - Main FastAPI Application

主应用入口文件
"""

import argparse
import logging
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add the backend directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import application configurations and components
from app.config import ServerConfig, ClaudeConfig
from app.config.logging_config import LoggingConfig
from app.utils.exceptions import register_exception_handlers
from app.db.base import init_db, dispose_db
from app.core.claude_service import session_claude_manager

# Import API routers
from app.api import (
    session_router,
    chat_router,
    github_router,
    workspace_router,
)

# Initialize logging
LoggingConfig().setup_logging()

# Initialize logger (after logging setup)
logger = logging.getLogger(__name__)

# Setup Claude environment variables
ClaudeConfig.setup_environment()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI应用生命周期管理
    
    处理启动和关闭事件:
    - 数据库初始化
    - Claude会话管理器清理任务
    """
    # Startup
    logger.info("=" * 80)
    logger.info("Starting Claude Code Web Platform...")
    logger.info("=" * 80)
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.warning("Application will start but database operations may fail")
    
    # Start Claude session cleanup task
    try:
        await session_claude_manager.start_cleanup_task()
        logger.info("Claude session manager started")
    except Exception as e:
        logger.error(f"Claude session manager failed to start: {e}")
    
    logger.info("Application startup complete")
    logger.info(f"Server URL: http://{ServerConfig.HOST}:{ServerConfig.PORT}")
    logger.info(f"Documentation: http://{ServerConfig.HOST}:{ServerConfig.PORT}/docs")
    logger.info(f"Health Check: http://{ServerConfig.HOST}:{ServerConfig.PORT}/health")
    logger.info("=" * 80)
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    # Stop Claude session cleanup task
    try:
        await session_claude_manager.stop_cleanup_task()
        await session_claude_manager.close_all()
        logger.info("Claude session manager stopped")
    except Exception as e:
        logger.error(f"Error stopping Claude session manager: {e}")
    
    # Close database connections
    try:
        await dispose_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")
    
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """
    创建并配置FastAPI应用
    
    Returns:
        配置好的FastAPI应用实例
    """
    app = FastAPI(
        title="Claude Code Web Platform",
        version="1.0.0",
        description="Web-based Claude Code programming platform with multi-turn conversation support",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Add CORS middleware (must be first)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ServerConfig.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Process-Time"],
    )

    # Register global exception handlers
    register_exception_handlers(app)

    # Include routers with /api prefix
    app.include_router(session_router, prefix="/api/code")
    app.include_router(chat_router, prefix="/api/code")
    app.include_router(github_router, prefix="/api/code")
    app.include_router(workspace_router, prefix="/api/code")

    return app


def run_api(host: str, port: int, **kwargs):
    """
    使用给定配置运行API服务器
    """
    try:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=kwargs.get("reload") or ServerConfig.RELOAD
        )
    except Exception as e:
        logger.error(f"Failed to start API server: {e}")
        raise


def main() -> None:
    """
    Claude Code Web Platform主入口
    """
    try:
        logger.info("=" * 80)
        logger.info("Starting Claude Code Web Platform...")
        logger.info("=" * 80)

        logger.info("\n" + "=" * 80)
        logger.info("Server Information:")
        logger.info(f"  - Server URL: http://{ServerConfig.HOST}:{ServerConfig.PORT}")
        logger.info(f"  - Documentation: http://{ServerConfig.HOST}:{ServerConfig.PORT}/docs")
        logger.info(f"  - Health Check: http://{ServerConfig.HOST}:{ServerConfig.PORT}/health")
        logger.info("=" * 80)

        # Start the server
        run_api(
            host=ServerConfig.HOST,
            port=ServerConfig.PORT,
            reload=ServerConfig.RELOAD
        )

    except KeyboardInterrupt:
        logger.info("\nShutting down Claude Code Web Platform gracefully...")
    except Exception as e:
        error_msg = f"Error starting server: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


# Create the app instance
app = create_app()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='claude-code-web',
                                     description='Claude Code Web Platform Server')
    parser.add_argument("--host", type=str, default=ServerConfig.HOST)
    parser.add_argument("--port", type=int, default=ServerConfig.PORT)
    parser.add_argument("--reload", action="store_true", default=ServerConfig.RELOAD)

    args = parser.parse_args()

    try:
        logger.info("=" * 80)
        logger.info("Starting Claude Code Web Platform Server...")
        logger.info("=" * 80)
        logger.info(f"  - Server URL: http://{args.host}:{args.port}")
        logger.info(f"  - Documentation: http://{args.host}:{args.port}/docs")
        logger.info(f"  - Health Check: http://{args.host}:{args.port}/health")
        logger.info("=" * 80)

        run_api(
            host=args.host,
            port=args.port,
            reload=args.reload
        )
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        sys.exit(1)
