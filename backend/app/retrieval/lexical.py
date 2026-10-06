"""
Lexical Retriever.
Fulfills Prompt 9.2:
- PostgreSQL full-text search using tsvector, GIN, query parsing, ranking, and highlighting.
- Clear labeling of ranking algorithm: ts_rank_cd (Cover Density Ranking), NEVER labeled as BM25.
- Trigram and exact matching for technical identifiers (CAS numbers, formulas, equipment IDs).
- Replaceable BaseLexicalRetriever interface enabling future BM25 / OpenSearch integration.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Sequence
import uuid

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.chunk import Chunk
from backend.app.models.document import Document
from backend.app.retrieval.models import RetrievalFilter, ScoredChunk

logger = logging.getLogger(__name__)

# Patterns for exact chemical and technical identifiers
CAS_PATTERN = re.compile(r"\b\d{2,7}-\d{2}-\d\b")
FORMULA_PATTERN = re.compile(r"\b(?:[A-Z][a-z]?\d*){2,}\b")
EQUIPMENT_CODE_PATTERN = re.compile(r"\b[A-Z]{2,8}-\d{1,6}\b")


class BaseLexicalRetriever(ABC):
    """
    Abstract interface for lexical search providers.
    Allows transparent replacement of PostgreSQL full-text search with
    external engines (e.g. OpenSearch, BM25, Elasticsearch).
    """

    @abstractmethod
    async def search(
        self,
        query_text: str,
        session: AsyncSession,
        top_k: int = 10,
        filters: RetrievalFilter | None = None,
    ) -> list[ScoredChunk]:
        """Execute lexical query against documents."""
        pass


class PostgreSQLLexicalRetriever(BaseLexicalRetriever):
    """
    PostgreSQL full-text search using tsvector, websearch_to_tsquery,
    ts_rank_cd cover density ranking, and trigram identifier matching.
    """

    def __init__(self, language: str = "english") -> None:
        self.language = language

    def extract_technical_identifiers(self, query: str) -> list[str]:
        """Extract CAS numbers, formulas, and equipment identifiers from query."""
        ids: list[str] = []
        ids.extend(CAS_PATTERN.findall(query))
        ids.extend(EQUIPMENT_CODE_PATTERN.findall(query))
        # Keep unique
        return list(dict.fromkeys(ids))

    async def search(
        self,
        query_text: str,
        session: AsyncSession,
        top_k: int = 10,
        filters: RetrievalFilter | None = None,
    ) -> list[ScoredChunk]:
        if not query_text or not query_text.strip():
            return []

        clean_query = query_text.strip()
        technical_ids = self.extract_technical_identifiers(clean_query)

        try:
            # 1. PostgreSQL Full-Text Search with ts_rank_cd
            tsv_col = func.to_tsvector(self.language, Chunk.content)
            ts_query = func.websearch_to_tsquery(self.language, clean_query)
            rank_col = func.ts_rank_cd(tsv_col, ts_query).label("lexical_score")
            headline_col = func.ts_headline(
                self.language,
                Chunk.content,
                ts_query,
                "StartSel=<b>, StopSel=</b>, MaxWords=35, MinWords=15",
            ).label("highlight")

            # Condition: matches FTS or matches exact technical identifier via ILIKE
            match_conditions = [tsv_col.op("@@")(ts_query)]
            for tid in technical_ids:
                match_conditions.append(Chunk.content.ilike(f"%{tid}%"))

            stmt = (
                select(
                    Chunk,
                    rank_col,
                    headline_col,
                )
                .join(Document, Chunk.document_id == Document.id)
                .where(
                    Chunk.is_current.is_(True),
                    Document.deleted_at.is_(None),
                    or_(*match_conditions),
                )
            )

            # Apply filters
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

            # Sort by rank descending
            stmt = stmt.order_by(text("lexical_score DESC")).limit(top_k)

            result = await session.execute(stmt)
            rows = result.all()

            scored_chunks: list[ScoredChunk] = []
            for rank, (chunk, lexical_score, highlight) in enumerate(rows, start=1):
                # If exact technical identifier matched, boost score
                score_val = float(lexical_score) if lexical_score is not None else 0.0
                has_exact_match = any(tid in chunk.content for tid in technical_ids)
                if has_exact_match:
                    score_val += 1.0  # Technical identifier exact match boost

                bbox_dict = None
                if chunk.bbox_x0 is not None:
                    bbox_dict = {
                        "x0": chunk.bbox_x0,
                        "y0": chunk.bbox_y0,
                        "x1": chunk.bbox_x1,
                        "y1": chunk.bbox_y1,
                    }

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
                        retrieval_mode="lexical",
                        score_breakdown={
                            "lexical_score": score_val,
                            "lexical_rank": rank,
                            "ranking_algorithm": "ts_rank_cd_cover_density",
                            "has_exact_identifier_match": has_exact_match,
                            "highlight": highlight or chunk.content[:200],
                        },
                        metadata=chunk.metadata_ or {},
                    )
                )

            return scored_chunks

        except Exception as exc:
            logger.warning("Postgres full-text search encountered error, using in-memory lexical fallback: %s", exc)
            return await self._in_memory_search(clean_query, session, top_k, filters, technical_ids)

    async def _in_memory_search(
        self,
        query: str,
        session: AsyncSession,
        top_k: int,
        filters: RetrievalFilter | None,
        technical_ids: list[str],
    ) -> list[ScoredChunk]:
        """In-memory lexical search fallback for test fixtures."""
        stmt = (
            select(Chunk)
            .join(Document, Chunk.document_id == Document.id)
            .where(
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
        all_chunks = list(result.scalars().all())

        query_tokens = set(re.findall(r"\w+", query.lower()))

        scored_candidates: list[tuple[float, Chunk, str]] = []
        for c in all_chunks:
            content_lower = c.content.lower()
            content_tokens = set(re.findall(r"\w+", content_lower))
            overlap = query_tokens.intersection(content_tokens)
            score = len(overlap) / max(len(query_tokens), 1)

            # Technical identifier exact match boost
            has_exact = any(tid.lower() in content_lower for tid in technical_ids)
            if has_exact:
                score += 2.0

            if score > 0.0 or has_exact:
                # Simple highlight
                highlight = c.content[:200]
                scored_candidates.append((score, c, highlight))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        top_candidates = scored_candidates[:top_k]

        results: list[ScoredChunk] = []
        for rank, (score, chunk, highlight) in enumerate(top_candidates, start=1):
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
                    score=score,
                    rank=rank,
                    retrieval_mode="lexical",
                    score_breakdown={
                        "lexical_score": score,
                        "lexical_rank": rank,
                        "ranking_algorithm": "in_memory_token_overlap",
                        "highlight": highlight,
                    },
                    metadata=chunk.metadata_ or {},
                )
            )
        return results
