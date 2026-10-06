"""
Semantic Retriever.
Fulfills Prompt 9.1:
- pgvector cosine retrieval with configurable top-K.
- Metadata filters: tenant (organization_id), document_id, section_id, date range, and chemical flags.
- Configurable HNSW query-time search parameters (hnsw.ef_search).
- Graceful test fallback with in-memory numpy cosine similarity.
"""

from __future__ import annotations

import logging
from typing import Any, Sequence
import uuid

import numpy as np
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.embeddings.base import BaseEmbeddingProvider
from backend.app.embeddings.factory import get_text_embedding_provider
from backend.app.embeddings.text_embedder import TextEmbeddingService
from backend.app.models.chunk import Chunk, ChunkEmbedding, EmbeddingModelType
from backend.app.models.document import Document
from backend.app.retrieval.models import RetrievalFilter, ScoredChunk

logger = logging.getLogger(__name__)


class SemanticRetriever:
    """
    Executes semantic similarity vector search using pgvector cosine distance.
    Supports granular metadata filtering and query-time HNSW tuning.
    """

    def __init__(
        self,
        embedding_provider: BaseEmbeddingProvider | None = None,
        embedding_service: TextEmbeddingService | None = None,
        default_ef_search: int = 100,
    ) -> None:
        self.provider = embedding_provider or get_text_embedding_provider()
        self.embedding_service = embedding_service or TextEmbeddingService(provider=self.provider)
        self.default_ef_search = default_ef_search

    async def get_query_embedding(self, query_text: str) -> list[float]:
        """Generate embedding vector for the query string."""
        emb_res = await self.provider.embed_single(query_text)
        return emb_res.vector

    async def search(
        self,
        query_text: str,
        session: AsyncSession,
        top_k: int = 10,
        filters: RetrievalFilter | None = None,
        ef_search: int | None = None,
        query_vector: list[float] | None = None,
    ) -> list[ScoredChunk]:
        """
        Execute filtered semantic cosine retrieval.
        """
        if not query_text and query_vector is None:
            return []

        # 1. Compute or use provided query vector
        vec = query_vector if query_vector is not None else await self.get_query_embedding(query_text)

        # 2. Configure HNSW ef_search at session level if specified
        target_ef = ef_search or self.default_ef_search
        try:
            await session.execute(text(f"SET LOCAL hnsw.ef_search = {int(target_ef)}"))
        except Exception as exc:
            # Tolerant on SQLite / test sessions
            logger.debug("Could not set local hnsw.ef_search (safe in non-pgvector environments): %s", exc)

        # 3. Build query with pgvector cosine distance
        # Cosine distance: ChunkEmbedding.embedding <=> vec
        # Cosine similarity = 1.0 - distance
        dist_expr = ChunkEmbedding.embedding.cosine_distance(vec).label("distance")
        sim_expr = (1.0 - ChunkEmbedding.embedding.cosine_distance(vec)).label("similarity")

        stmt = (
            select(
                Chunk,
                ChunkEmbedding,
                dist_expr,
                sim_expr,
            )
            .join(Chunk, ChunkEmbedding.chunk_id == Chunk.id)
            .join(Document, Chunk.document_id == Document.id)
            .where(
                ChunkEmbedding.embedding_type == EmbeddingModelType.TEXT,
                Chunk.is_current.is_(True),
                Document.deleted_at.is_(None),
            )
        )

        # 4. Apply metadata filters
        if filters:
            if filters.organization_id is not None:
                stmt = stmt.where(Document.organization_id == filters.organization_id)
            if filters.document_ids:
                stmt = stmt.where(Chunk.document_id.in_(filters.document_ids))
            if filters.section_ids:
                stmt = stmt.where(Chunk.section_id.in_(filters.section_ids))
            if filters.chunk_types:
                stmt = stmt.where(Chunk.chunk_type.in_(filters.chunk_types))
            if filters.date_from is not None:
                stmt = stmt.where(Chunk.created_at >= filters.date_from)
            if filters.date_to is not None:
                stmt = stmt.where(Chunk.created_at <= filters.date_to)
            if filters.contains_chemical_entities is not None:
                stmt = stmt.where(Chunk.contains_chemical_entities == filters.contains_chemical_entities)

        # Order by cosine distance ascending and limit top_k
        stmt = stmt.order_by(text("distance ASC")).limit(top_k)

        try:
            result = await session.execute(stmt)
            rows = result.all()
            scored_chunks: list[ScoredChunk] = []

            for rank, (chunk, chunk_emb, distance, similarity) in enumerate(rows, start=1):
                bbox_dict = None
                if chunk.bbox_x0 is not None:
                    bbox_dict = {
                        "x0": chunk.bbox_x0,
                        "y0": chunk.bbox_y0,
                        "x1": chunk.bbox_x1,
                        "y1": chunk.bbox_y1,
                    }

                score_val = float(similarity) if similarity is not None else max(0.0, 1.0 - float(distance))
                scored_chunks.append(
                    ScoredChunk(
                        chunk_id=chunk.id,
                        document_id=chunk.document_id,
                        content=chunk.content,
                        raw_text=chunk.content,
                        retrieval_text=chunk.content,
                        display_text=chunk.content,
                        chunk_type=chunk.chunk_type,
                        chunk_index=chunk.chunk_index,
                        page_number=chunk.page_number,
                        bbox=bbox_dict,
                        score=score_val,
                        rank=rank,
                        retrieval_mode="semantic",
                        score_breakdown={
                            "semantic_score": score_val,
                            "semantic_distance": float(distance) if distance is not None else None,
                            "semantic_rank": rank,
                            "model_name": chunk_emb.model_name,
                        },
                        metadata=chunk.metadata_ or {},
                    )
                )

            return scored_chunks

        except Exception as query_exc:
            logger.warning("Postgres pgvector query encountered error, using in-memory vector evaluation: %s", query_exc)
            # In-memory evaluation fallback for tests / environments without live pgvector
            return await self._in_memory_search(query_text, session, top_k, filters, vec)

    async def _in_memory_search(
        self,
        query_text: str,
        session: AsyncSession,
        top_k: int,
        filters: RetrievalFilter | None,
        query_vec: list[float],
    ) -> list[ScoredChunk]:
        """In-memory cosine similarity fallback for test fixtures."""
        stmt = (
            select(Chunk, ChunkEmbedding)
            .join(Chunk, ChunkEmbedding.chunk_id == Chunk.id)
            .join(Document, Chunk.document_id == Document.id)
            .where(
                ChunkEmbedding.embedding_type == EmbeddingModelType.TEXT,
                Chunk.is_current.is_(True),
                Document.deleted_at.is_(None),
            )
        )
        if filters:
            if filters.organization_id is not None:
                stmt = stmt.where(Document.organization_id == filters.organization_id)
            if filters.document_ids:
                stmt = stmt.where(Chunk.document_id.in_(filters.document_ids))
            if filters.section_ids:
                stmt = stmt.where(Chunk.section_id.in_(filters.section_ids))
            if filters.chunk_types:
                stmt = stmt.where(Chunk.chunk_type.in_(filters.chunk_types))
            if filters.date_from is not None:
                stmt = stmt.where(Chunk.created_at >= filters.date_from)
            if filters.date_to is not None:
                stmt = stmt.where(Chunk.created_at <= filters.date_to)
            if filters.contains_chemical_entities is not None:
                stmt = stmt.where(Chunk.contains_chemical_entities == filters.contains_chemical_entities)

        result = await session.execute(stmt)
        candidates = result.all()

        q_arr = np.array(query_vec, dtype=np.float32)
        q_norm = np.linalg.norm(q_arr)
        if q_norm == 0:
            return []

        scored: list[tuple[float, Chunk, ChunkEmbedding]] = []
        for chunk, chunk_emb in candidates:
            v_arr = np.array(chunk_emb.embedding, dtype=np.float32)
            v_norm = np.linalg.norm(v_arr)
            sim = float(np.dot(q_arr, v_arr) / (q_norm * v_norm)) if v_norm > 0 else 0.0
            scored.append((sim, chunk, chunk_emb))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_candidates = scored[:top_k]

        results: list[ScoredChunk] = []
        for rank, (sim, chunk, chunk_emb) in enumerate(top_candidates, start=1):
            bbox_dict = None
            if chunk.bbox_x0 is not None:
                bbox_dict = {
                    "x0": chunk.bbox_x0,
                    "y0": chunk.bbox_y0,
                    "x1": chunk.bbox_x1,
                    "y1": chunk.bbox_y1,
                }
            results.append(
                ScoredChunk(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    content=chunk.content,
                    raw_text=chunk.content,
                    retrieval_text=chunk.content,
                    display_text=chunk.content,
                    chunk_type=chunk.chunk_type,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    bbox=bbox_dict,
                    score=sim,
                    rank=rank,
                    retrieval_mode="semantic",
                    score_breakdown={
                        "semantic_score": sim,
                        "semantic_rank": rank,
                        "model_name": chunk_emb.model_name,
                    },
                    metadata=chunk.metadata_ or {},
                )
            )
        return results
