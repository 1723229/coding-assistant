"""
Base repository pattern implementation

Provides abstract base repository class with common CRUD operations
with async support.
"""

from abc import ABC
from typing import Any, Dict, Generic, List, Optional, TypeVar, Type

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_with_session

# Generic type variables
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType], ABC):
    """
    Asynchronous base Repository class, providing common CRUD operations
    
    Generic parameters:
        ModelType: SQLAlchemy model type
        CreateSchemaType: Schema type for create operations
        UpdateSchemaType: Schema type for update operations
    """

    def __init__(self, model: Type[ModelType]):
        """
        Initialize Repository
        
        Args:
            model: SQLAlchemy model class
        """
        self.model = model

    async def get_by_id(self, session: AsyncSession, record_id: Any) -> Optional[ModelType]:
        """
        Get single record by ID
        
        Args:
            session: Asynchronous database session
            record_id: Record ID
            
        Returns:
            Model instance or None
        """
        # Dynamically get primary key field
        pk_column = list(self.model.__table__.primary_key.columns)[0]
        stmt = select(self.model).where(pk_column == record_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
            self,
            session: AsyncSession,
            skip: int = 0,
            limit: int = 100,
            filters: Dict[str, Any] = None,
            order_by: str = None
    ) -> List[ModelType]:
        """
        Get multiple records
        
        Args:
            session: Asynchronous database session
            skip: Number of records to skip
            limit: Maximum number of records
            filters: Filter condition dictionary
            order_by: Sort field
            
        Returns:
            List of model instances
        """
        stmt = select(self.model)

        # Apply filter conditions
        if filters:
            stmt = self._apply_filters(stmt, filters)

        # Apply sorting
        if order_by:
            stmt = self._apply_order_by(stmt, order_by)

        stmt = stmt.offset(skip).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, session: AsyncSession, filters: Dict[str, Any] = None) -> int:
        """
        Count records
        
        Args:
            session: Asynchronous database session
            filters: Filter condition dictionary
            
        Returns:
            Record count
        """
        pk_column = list(self.model.__table__.primary_key.columns)[0]
        stmt = select(func.count(pk_column))

        if filters:
            stmt = self._apply_filters(stmt, filters)

        result = await session.execute(stmt)
        return result.scalar() or 0

    async def create(self, session: AsyncSession, obj_in: CreateSchemaType, **kwargs) -> ModelType:
        """
        Create new record
        
        Args:
            session: Asynchronous database session
            obj_in: Creation data
            **kwargs: Extra parameters
            
        Returns:
            Created model instance
        """
        # If it's a dictionary, use directly; if it's a Pydantic model, convert to dictionary
        if hasattr(obj_in, 'model_dump'):
            obj_data = obj_in.model_dump(exclude_unset=True)
        elif hasattr(obj_in, 'dict'):
            obj_data = obj_in.dict(exclude_unset=True)
        else:
            obj_data = dict(obj_in) if obj_in else {}

        # Merge extra parameters
        obj_data.update(kwargs)

        db_obj = self.model(**obj_data)
        session.add(db_obj)
        await session.flush()  # Get ID but don't commit
        await session.refresh(db_obj)
        return db_obj

    async def update(
            self,
            session: AsyncSession,
            db_obj: ModelType,
            obj_in: UpdateSchemaType,
            **kwargs
    ) -> ModelType:
        """
        Update record
        
        Args:
            session: Asynchronous database session
            db_obj: Model instance to update
            obj_in: Update data
            **kwargs: Extra parameters
            
        Returns:
            Updated model instance
        """
        # Get update data
        if hasattr(obj_in, 'model_dump'):
            update_data = obj_in.model_dump(exclude_unset=True)
        elif hasattr(obj_in, 'dict'):
            update_data = obj_in.dict(exclude_unset=True)
        else:
            update_data = dict(obj_in) if obj_in else {}

        # Merge extra parameters
        update_data.update(kwargs)

        # Merge the object into this session if it's detached
        if not session.object_session(db_obj):
            db_obj = await session.merge(db_obj)
        
        # Update fields
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        await session.flush()
        await session.refresh(db_obj)
        return db_obj

    async def delete(self, session: AsyncSession, record_id: Any) -> Optional[ModelType]:
        """
        Delete record
        
        Args:
            session: Asynchronous database session
            record_id: Record ID
            
        Returns:
            Deleted model instance or None
        """
        # First get the object to delete
        obj = await self.get_by_id(session, record_id)
        if obj:
            await session.delete(obj)
            await session.flush()
        return obj

    def _apply_filters(self, stmt, filters: Dict[str, Any]):
        """
        Apply filter conditions
        
        Args:
            stmt: SQLAlchemy query statement
            filters: Filter condition dictionary
            
        Returns:
            Query statement with filters applied
        """
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                column = getattr(self.model, key)

                # Handle special filter conditions
                if isinstance(value, dict):
                    # Range query {"gte": 1, "lte": 10}
                    if "gte" in value:
                        stmt = stmt.where(column >= value["gte"])
                    if "lte" in value:
                        stmt = stmt.where(column <= value["lte"])
                    if "gt" in value:
                        stmt = stmt.where(column > value["gt"])
                    if "lt" in value:
                        stmt = stmt.where(column < value["lt"])
                    if "like" in value:
                        stmt = stmt.where(column.like(f"%{value['like']}%"))
                    if "in" in value:
                        stmt = stmt.where(column.in_(value["in"]))
                else:
                    # Exact match
                    stmt = stmt.where(column == value)

        return stmt

    def _apply_order_by(self, stmt, order_by: str):
        """
        Apply sorting
        
        Args:
            stmt: SQLAlchemy query statement
            order_by: Sort field, supports "field" or "-field" (descending)
            
        Returns:
            Query statement with sorting applied
        """
        if order_by.startswith("-"):
            # Descending
            field = order_by[1:]
            if hasattr(self.model, field):
                stmt = stmt.order_by(getattr(self.model, field).desc())
        else:
            # Ascending
            if hasattr(self.model, order_by):
                stmt = stmt.order_by(getattr(self.model, order_by))

        return stmt


