"""
ChemRAG — Document Repository
==============================
Provides persistence operations for Document and DocumentVersion entities.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.document import Document, DocumentVersion
from backend.app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """
    Repository for managing Document and DocumentVersion entities.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Document, session)

    async def get_by_sha256(self, file_hash_sha256: str) -> Optional[Document]:
        """Find a document by its file SHA-256 hash."""
        result = await self.session.execute(
            select(Document).where(Document.file_hash_sha256 == file_hash_sha256)
        )
        return result.scalars().first()

    async def get_with_versions(self, document_id: uuid.UUID) -> Optional[Document]:
        """Fetch document along with all its versions."""
        result = await self.session.execute(
            select(Document)
            .options(selectinload(Document.versions))
            .where(Document.id == document_id)
        )
        return result.scalars().first()

    async def add_version(
        self, document_id: uuid.UUID, version_data: dict
    ) -> DocumentVersion:
        """Create a new version for a document."""
        version = DocumentVersion(document_id=document_id, **version_data)
        self.session.add(version)
        await self.session.flush()
        return version
