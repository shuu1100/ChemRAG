"""
ChemRAG — Vector Embedding Repository
=====================================
Provides vector storage and pgvector similarity search operations for ChunkEmbedding.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.chunk import Chunk, ChunkEmbedding, EmbeddingModelType
from backend.app.repositories.base import BaseRepository


class EmbeddingRepository(BaseRepository[ChunkEmbedding]):
    """
    Repository for managing vector embeddings and performing pgvector similarity search.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ChunkEmbedding, session)

    async def save_embedding(
        self,
        chunk_id: uuid.UUID,
        embedding: List[float],
        model_name: str,
        embedding_type: EmbeddingModelType = EmbeddingModelType.TEXT,
        model_version: Optional[str] = None,
    ) -> ChunkEmbedding:
        """
        Store or update a vector embedding for a chunk.
        """
        dimensions = len(embedding)
        # Check if embedding already exists for this chunk/model/type
        result = await self.session.execute(
            select(ChunkEmbedding).where(
                ChunkEmbedding.chunk_id == chunk_id,
                ChunkEmbedding.model_name == model_name,
                ChunkEmbedding.embedding_type == embedding_type,
            )
        )
        existing = result.scalars().first()

        if existing:
            existing.embedding = embedding
            existing.dimensions = dimensions
            existing.model_version = model_version
            await self.session.flush()
            return existing

        db_obj = ChunkEmbedding(
            chunk_id=chunk_id,
            embedding_type=embedding_type,
            model_name=model_name,
            model_version=model_version,
            dimensions=dimensions,
            embedding=embedding,
        )
        self.session.add(db_obj)
        await self.session.flush()
        return db_obj

    async def search_similar(
        self,
        query_vector: List[float],
        top_k: int = 10,
        model_name: Optional[str] = None,
        embedding_type: EmbeddingModelType = EmbeddingModelType.TEXT,
        distance_metric: str = "cosine",
    ) -> List[Tuple[Chunk, float]]:
        """
        Perform vector similarity search against pgvector.
        Returns a list of (Chunk, distance_score) tuples.
        """
        if distance_metric == "cosine":
            # Cosine distance operator in pgvector: <=>
            dist_col = ChunkEmbedding.embedding.cosine_distance(query_vector)
        elif distance_metric == "l2":
            # L2 Euclidean distance operator in pgvector: <->
            dist_col = ChunkEmbedding.embedding.l2_distance(query_vector)
        elif distance_metric == "inner_product":
            # Max Inner Product operator in pgvector: <#>
            dist_col = ChunkEmbedding.embedding.max_inner_product(query_vector)
        else:
            dist_col = ChunkEmbedding.embedding.cosine_distance(query_vector)

        query = (
            select(Chunk, dist_col.label("distance"))
            .join(ChunkEmbedding, Chunk.id == ChunkEmbedding.chunk_id)
            .where(Chunk.is_current.is_(True))
        )

        if model_name:
            query = query.where(ChunkEmbedding.model_name == model_name)

        query = query.where(ChunkEmbedding.embedding_type == embedding_type)
        query = query.order_by(dist_col).limit(top_k)

        result = await self.session.execute(query)
        rows = result.all()
        return [(row[0], float(row[1])) for row in rows]
