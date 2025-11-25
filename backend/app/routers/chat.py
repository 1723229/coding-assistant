"""WebSocket chat endpoint with streaming support."""

import json
import asyncio
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session_maker
from ..models import Session, Message
from ..services.claude_service import ClaudeService, ChatMessage, session_claude_manager
from ..config import get_settings

router = APIRouter()
settings = get_settings()


class ConnectionManager:
    """WebSocket connection manager."""
    
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
    
    async def connect(self, session_id: str, websocket: WebSocket):
        """Connect a WebSocket."""
        self.active_connections[session_id] = websocket
    
    def disconnect(self, session_id: str):
        """Disconnect a WebSocket."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    async def send_message(self, session_id: str, message: dict):
        """Send message to specific session."""
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connections."""
        for connection in self.active_connections.values():
            await connection.send_json(message)


manager = ConnectionManager()


def chat_message_to_dict(msg: ChatMessage) -> dict:
    """Convert ChatMessage to dict for JSON serialization."""
    return {
        "type": msg.type,
        "content": msg.content,
        "tool_name": msg.tool_name,
        "tool_input": msg.tool_input,
        "metadata": msg.metadata,
        "timestamp": datetime.utcnow().isoformat(),
    }


async def save_message(
    session_id: str,
    role: str,
    content: str,
    tool_name: Optional[str] = None,
    tool_input: Optional[str] = None,
    tool_result: Optional[str] = None,
):
    """Save message to database."""
    async with async_session_maker() as db:
        message = Message(
            session_id=session_id,
            role=role,
            content=content,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_result=tool_result,
        )
        db.add(message)
        await db.commit()


@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for chat with streaming responses."""
    
    # Accept the WebSocket connection FIRST
    await websocket.accept()
    print(f"[WS] Connection accepted for session: {session_id}")
    
    # Now get session info
    try:
        async with async_session_maker() as db:
            result = await db.execute(
                select(Session).where(Session.id == session_id)
            )
            session = result.scalar_one_or_none()
            
            if not session:
                print(f"[WS] Session not found: {session_id}")
                await websocket.send_json({
                    "type": "error",
                    "content": f"Session not found: {session_id}",
                })
                await websocket.close(code=4004, reason="Session not found")
                return
            
            workspace_path = session.workspace_path
            print(f"[WS] Found session: {session.name}, workspace: {workspace_path}")
    except Exception as e:
        print(f"[WS] Database error: {e}")
        await websocket.send_json({
            "type": "error",
            "content": f"Database error: {str(e)}",
        })
        await websocket.close(code=4005, reason=f"Database error")
        return
    
    await manager.connect(session_id, websocket)
    print(f"[WS] Manager registered connection for session: {session_id}")
    
    # Send connection confirmation
    await websocket.send_json({
        "type": "connected",
        "session_id": session_id,
        "message": "Connected to chat session",
    })
    print(f"[WS] Sent connection confirmation to session: {session_id}")
    
    try:
        while True:
            # Wait for user message
            data = await websocket.receive_json()
            print(f"[WS] Received data: {data}")
            
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            
            if data.get("type") == "message":
                user_message = data.get("content", "")
                print(f"[WS] User message: {user_message[:50]}...")
                
                if not user_message.strip():
                    continue
                
                # Save user message
                await save_message(session_id, "user", user_message)
                
                # Send acknowledgment
                await websocket.send_json({
                    "type": "user_message_received",
                    "content": user_message,
                })
                
                # Create Claude service for this session
                claude_service = await session_claude_manager.get_service(
                    session_id=session_id,
                    workspace_path=workspace_path,
                )
                
                # Stream responses
                full_response = []
                try:
                    async for chat_msg in claude_service.chat_stream(user_message):
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
                    print(f"[WS] Error during chat: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "content": str(e),
                    })
            
            elif data.get("type") == "interrupt":
                # Handle interrupt signal
                await websocket.send_json({
                    "type": "interrupted",
                    "message": "Request interrupted",
                })
    
    except WebSocketDisconnect:
        print(f"[WS] Client disconnected: {session_id}")
        manager.disconnect(session_id)
    except Exception as e:
        print(f"[WS] Error: {e}")
        manager.disconnect(session_id)
        raise


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get chat history for a session."""
    async with async_session_maker() as db:
        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
        )
        messages = result.scalars().all()
        
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
