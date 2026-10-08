"""
ChemRAG — Chunk Repository
==========================
Provides persistence operations for Chunk objects.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.chunk import Chunk
from backend.app.repositories.base import BaseRepository


class ChunkRepository(BaseRepository[Chunk]):
    """
    Repository for managing text and multimodal Chunk records.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Chunk, session)

    async def get_by_document(
        self, document_id: uuid.UUID, only_current: bool = True
    ) -> List[Chunk]:
        """Fetch all chunks belonging to a document."""
        query = select(Chunk).where(Chunk.document_id == document_id)
        if only_current:
            query = query.where(Chunk.is_current.is_(True))
        query = query.order_by(Chunk.chunk_index)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_with_embeddings(self, chunk_id: uuid.UUID) -> Optional[Chunk]:
        """Fetch chunk with associated vector embeddings."""
        result = await self.session.execute(
            select(Chunk)
            .options(selectinload(Chunk.embeddings))
            .where(Chunk.id == chunk_id)
        )
        return result.scalars().first()

    async def get_by_content_hash(self, content_hash: str) -> Optional[Chunk]:
        """Find chunk by content hash."""
        result = await self.session.execute(
            select(Chunk).where(Chunk.content_hash == content_hash)
        )
        return result.scalars().first()
