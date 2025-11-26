"""
Message repository implementation

Provides message-related data access methods.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.models.message import Message
from app.db.schemas.message import MessageCreate
from app.db.repository.base_repository import BaseRepository
from app.db.session import async_with_session


class MessageRepository(BaseRepository[Message, MessageCreate, None]):
    """
    Message data access layer
    
    Provides message-related database operations.
    """

    def __init__(self):
        super().__init__(Message)
    
    @async_with_session
    async def create_message(
        self,
        session: AsyncSession,
        session_id: str,
        role: str,
        content: str,
        tool_name: Optional[str] = None,
        tool_input: Optional[str] = None,
        tool_result: Optional[str] = None
    ) -> Message:
        """
        Create a new message
        
        Args:
            session: Database session
            session_id: Session UUID
            role: Message role (user, assistant, system)
            content: Message content
            tool_name: Tool name if tool was used
            tool_input: Tool input JSON
            tool_result: Tool result
            
        Returns:
            Created message object
        """
        message = Message(
            session_id=session_id,
            role=role,
            content=content,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_result=tool_result,
        )
        session.add(message)
        await session.flush()
        await session.refresh(message)
        return message
    
    @async_with_session
    async def get_session_messages(
        self,
        session: AsyncSession,
        session_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        """
        Get messages for a session
        
        Args:
            session: Database session
            session_id: Session UUID
            skip: Number to skip
            limit: Maximum number to return
            
        Returns:
            List of messages
        """
        stmt = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    @async_with_session
    async def get_message_count(
        self,
        session: AsyncSession,
        session_id: str
    ) -> int:
        """
        Get message count for a session
        
        Args:
            session: Database session
            session_id: Session UUID
            
        Returns:
            Number of messages
        """
        stmt = (
            select(func.count(Message.id))
            .where(Message.session_id == session_id)
        )
        result = await session.execute(stmt)
        return result.scalar() or 0
    
    @async_with_session
    async def get_last_messages(
        self,
        session: AsyncSession,
        session_id: str,
        count: int = 10
    ) -> List[Message]:
        """
        Get last N messages for a session
        
        Args:
            session: Database session
            session_id: Session UUID
            count: Number of messages to get
            
        Returns:
            List of messages (oldest first)
        """
        # Get the last N messages in descending order, then reverse
        stmt = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(count)
        )
        result = await session.execute(stmt)
        messages = list(result.scalars().all())
        return list(reversed(messages))
    
    @async_with_session
    async def delete_session_messages(
        self,
        session: AsyncSession,
        session_id: str
    ) -> int:
        """
        Delete all messages for a session
        
        Args:
            session: Database session
            session_id: Session UUID
            
        Returns:
            Number of deleted messages
        """
        stmt = select(Message).where(Message.session_id == session_id)
        result = await session.execute(stmt)
        messages = result.scalars().all()
        
        count = 0
        for message in messages:
            await session.delete(message)
            count += 1
        
        await session.flush()
        return count


