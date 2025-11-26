"""
WebSocket chat endpoint with streaming support.

Provides real-time chat functionality with Claude using WebSocket connections.
"""

import json
import asyncio
import logging
from typing import Optional, Dict
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.db import AsyncSessionLocal
from app.db.models import Session, Message
from app.db.repository import SessionRepository, MessageRepository
from app.services import ClaudeService, ChatMessage, session_claude_manager
from app.config import get_settings

from sqlalchemy import select

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)

# Repository instances
session_repo = SessionRepository()
message_repo = MessageRepository()


class ConnectionManager:
    """WebSocket connection manager for chat sessions."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, session_id: str, websocket: WebSocket):
        """Register a WebSocket connection."""
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected for session: {session_id}")
    
    def disconnect(self, session_id: str):
        """Unregister a WebSocket connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected for session: {session_id}")
    
    async def send_message(self, session_id: str, message: dict):
        """Send message to specific session."""
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connections."""
        for connection in self.active_connections.values():
            await connection.send_json(message)
    
    def is_connected(self, session_id: str) -> bool:
        """Check if session is connected."""
        return session_id in self.active_connections


manager = ConnectionManager()


def chat_message_to_dict(msg: ChatMessage) -> dict:
    """Convert ChatMessage to dict for JSON serialization."""
    return msg.to_dict()


async def save_message(
    session_id: str,
    role: str,
    content: str,
    tool_name: Optional[str] = None,
    tool_input: Optional[str] = None,
    tool_result: Optional[str] = None,
):
    """Save message to database using repository."""
    await message_repo.create_message(
        session_id=session_id,
        role=role,
        content=content,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_result=tool_result,
    )


@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for chat with streaming responses.
    
    Protocol:
    - Client sends: {"type": "message", "content": "..."}
    - Client sends: {"type": "ping"}
    - Client sends: {"type": "interrupt"}
    - Server sends: {"type": "connected", "session_id": "..."}
    - Server sends: {"type": "text", "content": "..."}
    - Server sends: {"type": "tool_use", "tool_name": "...", "tool_input": {...}}
    - Server sends: {"type": "response_complete"}
    - Server sends: {"type": "error", "content": "..."}
    """
    
    # Accept the WebSocket connection FIRST
    await websocket.accept()
    logger.info(f"[WS] Connection accepted for session: {session_id}")
    
    # Get session info
    try:
        session = await session_repo.get_session_by_id(session_id)
        
        if not session:
            logger.warning(f"[WS] Session not found: {session_id}")
            await websocket.send_json({
                "type": "error",
                "content": f"Session not found: {session_id}",
            })
            await websocket.close(code=4004, reason="Session not found")
            return
        
        workspace_path = session.workspace_path
        logger.info(f"[WS] Found session: {session.name}, workspace: {workspace_path}")
        
    except Exception as e:
        logger.error(f"[WS] Database error: {e}")
        await websocket.send_json({
            "type": "error",
            "content": f"Database error: {str(e)}",
        })
        await websocket.close(code=4005, reason="Database error")
        return
    
    await manager.connect(session_id, websocket)
    
    # Send connection confirmation
    await websocket.send_json({
        "type": "connected",
        "session_id": session_id,
        "message": "Connected to chat session",
    })
    
    try:
        while True:
            # Wait for user message
            data = await websocket.receive_json()
            logger.debug(f"[WS] Received data: {data}")
            
            message_type = data.get("type")
            
            if message_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            
            if message_type == "message":
                user_message = data.get("content", "")
                
                if not user_message.strip():
                    continue
                
                logger.info(f"[WS] User message: {user_message[:50]}...")
                
                # Save user message
                await save_message(session_id, "user", user_message)
                
                # Send acknowledgment
                await websocket.send_json({
                    "type": "user_message_received",
                    "content": user_message,
                })
                
                # Create Claude service for this session with multi-turn support
                claude_service = await session_claude_manager.get_service(
                    session_id=session_id,
                    workspace_path=workspace_path,
                )
                
                # Stream responses with session_id for multi-turn conversation
                full_response = []
                try:
                    async for chat_msg in claude_service.chat_stream(
                        user_message,
                        session_id=session_id,
                    ):
                        msg_dict = chat_message_to_dict(chat_msg)
                        await websocket.send_json(msg_dict)
                        
                        # Collect text for saving
                        if chat_msg.type in ("text", "text_delta"):
                            full_response.append(chat_msg.content)
                        
                        # Small delay to prevent flooding
                        await asyncio.sleep(0.01)
                    
                    # Save assistant response
                    if full_response:
                        await save_message(
                            session_id,
                            "assistant",
                            "".join(full_response),
                        )
                    
                    # Send completion signal
                    await websocket.send_json({
                        "type": "response_complete",
                    })
                    
                except Exception as e:
                    logger.error(f"[WS] Error during chat: {e}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "content": str(e),
                    })
            
            elif message_type == "interrupt":
                # Handle interrupt signal
                claude_service = await session_claude_manager.get_service(
                    session_id=session_id,
                    workspace_path=workspace_path,
                )
                await claude_service.interrupt()
                await websocket.send_json({
                    "type": "interrupted",
                    "message": "Request interrupted",
                })
    
    except WebSocketDisconnect:
        logger.info(f"[WS] Client disconnected: {session_id}")
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"[WS] Error: {e}", exc_info=True)
        manager.disconnect(session_id)
        raise


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get chat history for a session."""
    messages = await message_repo.get_session_messages(session_id=session_id)
    
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "tool_name": m.tool_name,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


@router.get("/stats/{session_id}")
async def get_session_stats(session_id: str):
    """Get Claude session statistics."""
    stats = session_claude_manager.get_session_stats(session_id)
    if stats is None:
        return {"session_id": session_id, "status": "not_found"}
    return stats


@router.get("/stats")
async def get_all_stats():
    """Get all Claude session statistics."""
    return session_claude_manager.get_all_stats()
