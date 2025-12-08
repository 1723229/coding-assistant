# -*- coding: utf-8 -*-
"""
Executor FastAPI service entry point.

This service runs inside a Docker container and provides API endpoints
for executing Claude Code tasks with SSE streaming support.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import uvicorn

from executor.config import config
from executor.api.task_router import task_router
from executor.services.agent_service import StreamingAgentService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Executor service starting up...")
    logger.info(f"Workspace root: {config.WORKSPACE_ROOT}")
    logger.info(f"Port: {config.PORT}")
    logger.info(f"Model: {config.ANTHROPIC_MODEL}")
    
    # Note: We don't change to workspace directory here because
    # the volume mount may not be ready yet at startup time.
    # The agent_service will handle directory changes per-session.
    
    yield
    
    # Shutdown
    logger.info("Executor service shutting down...")
    try:
        agent_service = StreamingAgentService()
        await agent_service.close_all_sessions()
    except Exception as e:
        logger.warning(f"Error during shutdown: {e}")
    logger.info("Executor service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Executor API",
    description="API for executing Claude Code tasks in sandbox containers with SSE streaming support",
    version="1.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(task_router)


# ===================
# Session Management Endpoints
# ===================

class SessionResponse(BaseModel):
    """Response model for session operations."""
    status: str
    message: str


class SessionListResponse(BaseModel):
    """Response model for listing sessions."""
    total: int
    sessions: list


@app.delete("/api/sessions/{session_id}", response_model=SessionResponse)
async def delete_session(session_id: str):
    """Delete an agent session."""
    logger.info(f"Received delete request for session: {session_id}")
    
    agent_service = StreamingAgentService()
    await agent_service.close_session(session_id)
    
    return SessionResponse(status="success", message="Session deleted")


@app.get("/api/sessions", response_model=SessionListResponse)
async def list_sessions():
    """List all active agent sessions."""
    agent_service = StreamingAgentService()
    sessions = agent_service.list_sessions()
    return SessionListResponse(total=len(sessions), sessions=sessions)


@app.delete("/api/sessions", response_model=SessionResponse)
async def close_all_sessions():
    """Close all agent sessions."""
    agent_service = StreamingAgentService()
    await agent_service.close_all_sessions()
    
    return SessionResponse(status="success", message="All sessions closed")


# ===================
# Health Check
# ===================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "executor",
        "port": config.PORT,
        "workspace": config.WORKSPACE_ROOT,
    }


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "Executor API",
        "version": "1.0.0",
        "description": "Claude Code execution service with SSE streaming",
        "endpoints": {
            "stream": "POST /api/tasks/stream",
            "cancel": "POST /api/tasks/cancel",
            "sessions": "GET /api/sessions",
            "health": "GET /health",
        }
    }


def main():
    """Main function for running the FastAPI server."""
    port = config.PORT
    logger.info(f"Starting executor service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
