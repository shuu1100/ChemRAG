"""
ChemRAG — Chemical Entity Repository
=====================================
Provides persistence and lookup operations for ChemicalEntity entities.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.chemical import ChemicalEntity
from backend.app.repositories.base import BaseRepository


class ChemicalRepository(BaseRepository[ChemicalEntity]):
    """
    Repository for storing and retrieving chemical entities by SMILES, InChIKey, or canonical name.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ChemicalEntity, session)

    async def get_by_inchikey(self, inchikey: str) -> Optional[ChemicalEntity]:
        """Find a chemical entity by standard InChIKey."""
        result = await self.session.execute(
            select(ChemicalEntity).where(ChemicalEntity.inchikey == inchikey)
        )
        return result.scalars().first()

    async def get_by_smiles(self, smiles: str) -> Optional[ChemicalEntity]:
        """Find a chemical entity by SMILES representation."""
        result = await self.session.execute(
            select(ChemicalEntity).where(ChemicalEntity.smiles == smiles)
        )
        return result.scalars().first()

    async def search_by_name(
        self, name_query: str, limit: int = 20
    ) -> List[ChemicalEntity]:
        """Search chemical entities matching name substring (case-insensitive)."""
        pattern = f"%{name_query}%"
        result = await self.session.execute(
            select(ChemicalEntity)
            .where(ChemicalEntity.canonical_name.ilike(pattern))
            .limit(limit)
        )
        return list(result.scalars().all())
