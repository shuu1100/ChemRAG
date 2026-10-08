"""
ChemRAG — Base Repository Pattern
==================================
Provides generic async CRUD operations for SQLAlchemy 2.0 models.
"""
from __future__ import annotations

import uuid
from typing import Any, Generic, List, Optional, Type, TypeVar

from sqlalchemy import func, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic Base Repository providing standardized async CRUD operations.
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, id: uuid.UUID | str | int) -> Optional[ModelType]:
        """Fetch a single record by primary key."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalars().first()

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[dict[str, Any]] = None,
    ) -> List[ModelType]:
        """List records with pagination and optional filter dictionary."""
        query = select(self.model)
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, obj_in: dict[str, Any] | ModelType) -> ModelType:
        """Create and flush a new record."""
        if isinstance(obj_in, dict):
            db_obj = self.model(**obj_in)
        else:
            db_obj = obj_in
        self.session.add(db_obj)
        await self.session.flush()
        return db_obj

    async def update(
        self, id: uuid.UUID | str | int, obj_in: dict[str, Any]
    ) -> Optional[ModelType]:
        """Update an existing record by primary key."""
        db_obj = await self.get_by_id(id)
        if db_obj is None:
            return None
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        await self.session.flush()
        return db_obj

    async def delete(self, id: uuid.UUID | str | int) -> bool:
        """Delete a record by primary key."""
        db_obj = await self.get_by_id(id)
        if db_obj is None:
            return False
        await self.session.delete(db_obj)
        await self.session.flush()
        return True

    async def count(self, filters: Optional[dict[str, Any]] = None) -> int:
        """Count total records matching filters."""
        query = select(func.count()).select_from(self.model)
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        result = await self.session.execute(query)
        return result.scalar() or 0
