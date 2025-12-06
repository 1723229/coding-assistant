#!/usr/bin/env python3
"""
Coding Assistant - Main FastAPI Application

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
from app.config import ServerConfig, ExecutorConfig
from app.config.logging_config import LoggingConfig
from app.utils.exceptions import register_exception_handlers
from app.db.base import init_db, dispose_db
from app.core.claude_service import session_manager

# Import API routers
from app.api import (
    session_router,
    chat_router,
    github_router,
    workspace_router,
    project_router,
    module_router,
    version_router,
)

# Initialize logging
LoggingConfig().setup_logging()

# Initialize logger (after logging setup)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI应用生命周期管理
    
    处理启动和关闭事件:
    - 数据库初始化
    - 会话管理器清理任务
    """
    # Startup
    logger.info("=" * 80)
    logger.info("Starting Coding Assistant...")
    logger.info("=" * 80)
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.warning("Application will start but database operations may fail")
    
    # Start session cleanup task
    # NOTE: 禁用自动清理任务，避免模块容器被误删
    # 如需清理，请手动调用 DELETE /api/code/container/{session_id}
    # try:
    #     await session_manager.start_cleanup_task()
    #     logger.info("Session manager started")
    # except Exception as e:
    #     logger.error(f"Session manager failed to start: {e}")
    logger.info("Session manager initialized (auto-cleanup disabled)")
    
    logger.info("Application startup complete")
    logger.info(f"Server URL: http://{ServerConfig.HOST}:{ServerConfig.PORT}")
    logger.info(f"Documentation: http://{ServerConfig.HOST}:{ServerConfig.PORT}/docs")
    logger.info(f"Health Check: http://{ServerConfig.HOST}:{ServerConfig.PORT}/health")
    logger.info("=" * 80)
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    # Stop session cleanup task (if enabled)
    # NOTE: 自动清理已禁用，关闭时不删除容器
    # try:
    #     await session_manager.stop_cleanup_task()
    #     await session_manager.close_all()
    #     logger.info("Session manager stopped")
    # except Exception as e:
    #     logger.error(f"Error stopping session manager: {e}")
    logger.info("Session manager shutdown (containers preserved)")
    
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
        title="Coding Assistant",
        version="1.0.0",
        description="AI-powered coding assistant with sandbox execution",
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
    app.include_router(project_router, prefix="/api/code")
    app.include_router(module_router, prefix="/api/code")
    app.include_router(version_router, prefix="/api/code")

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
    Coding Assistant主入口
    """
    try:
        logger.info("=" * 80)
        logger.info("Starting Coding Assistant...")
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
        logger.info("\nShutting down Coding Assistant gracefully...")
    except Exception as e:
        error_msg = f"Error starting server: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


# Create the app instance
app = create_app()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='coding-assistant',
                                     description='Coding Assistant Server')
    parser.add_argument("--host", type=str, default=ServerConfig.HOST)
    parser.add_argument("--port", type=int, default=ServerConfig.PORT)
    parser.add_argument("--reload", action="store_true", default=ServerConfig.RELOAD)

    args = parser.parse_args()

    try:
        logger.info("=" * 80)
        logger.info("Starting Coding Assistant Server...")
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
