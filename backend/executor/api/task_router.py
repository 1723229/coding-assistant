# -*- coding: utf-8 -*-
"""
Task API router with SSE streaming support.

This module provides endpoints for executing Claude Code tasks,
including a streaming endpoint that returns results via Server-Sent Events.
"""

import json
import asyncio
import logging
from typing import Optional, Dict, Any, AsyncGenerator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from executor.services.agent_service import StreamingAgentService

logger = logging.getLogger(__name__)

# Create router
task_router = APIRouter(prefix="/api/tasks", tags=["tasks"])

# Create service (singleton)
streaming_service = StreamingAgentService()


class ExecuteRequest(BaseModel):
    """Request model for task execution."""
    session_id: str
    workspace_path: str = "/workspace"
    prompt: str
    agent_type: str = "claude_code"
    allowed_tools: Optional[list] = None
    permission_mode: Optional[str] = None
    system_prompt: Optional[dict] = None
    model: Optional[str] = None
    task_type: Optional[str] = None  # "spec", "preview", "build"
    mcp_servers: Optional[dict] = None  # MCP server configurations
    spec_id: Optional[str] = None


class ExecuteResponse(BaseModel):
    """Response model for task execution."""
    status: str
    session_id: str
    text_content: Optional[str] = None
    tool_uses: Optional[list] = None
    thinking: Optional[list] = None
    metadata: Optional[dict] = None
    error_message: Optional[str] = None


class SessionResponse(BaseModel):
    """Response model for session operations."""
    status: str
    message: str


async def stream_generator(
    session_id: str,
    task_data: Dict[str, Any],
) -> AsyncGenerator[str, None]:
    """
    SSE stream generator for task execution.
    
    Yields SSE-formatted events as the task executes.
    Format: data: {json}\n\n
    
    If task_type is specified (spec, preview, build), uses OpenSpec flow.
    Otherwise, uses regular streaming execution.
    """
    try:
        yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
        await asyncio.sleep(0)
        
        task_type = task_data.get("task_type")
        
        if task_type in ("spec", "preview", "build"):
            async for event in streaming_service.execute_openspec_stream(task_data):
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0.01)
        else:
            async for event in streaming_service.execute_stream(task_data):
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0.01)
        
        yield f"data: {json.dumps({'type': 'response_complete'})}\n\n"
        
    except asyncio.CancelledError:
        logger.info(f"Stream cancelled: {session_id}")
        yield f"data: {json.dumps({'type': 'interrupted', 'message': 'Stream cancelled'})}\n\n"
        
    except Exception as e:
        logger.exception(f"Stream error: {session_id}")
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"


@task_router.post("/stream")
async def stream_task(request: ExecuteRequest):
    """
    Execute a task with SSE streaming response.
    
    This endpoint returns a Server-Sent Events stream that provides
    real-time updates as the task executes.
    
    Event types:
    - connected: Initial connection confirmation
    - text: Text content from the assistant
    - text_delta: Incremental text updates
    - tool_use: Tool invocation events
    - tool_result: Tool execution results
    - thinking: Model thinking/reasoning
    - system: System messages
    - result: Final result with metadata
    - error: Error messages
    - response_complete: Stream completion signal
    - interrupted: Stream was interrupted
    """
    logger.info(f"Received stream request for session: {request.session_id}")
    
    task_data = request.model_dump()
    
    return StreamingResponse(
        stream_generator(request.session_id, task_data),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@task_router.post("/cancel", response_model=SessionResponse)
async def cancel_task(session_id: str = Query(..., description="Session ID to cancel")):
    """Cancel a running task."""
    logger.info(f"Received cancel request for session: {session_id}")
    
    if streaming_service.cancel_task(session_id):
        return SessionResponse(status="success", message="Task cancelled")
    else:
        raise HTTPException(status_code=400, detail="No active task found for session")
