"""
Reranking data transfer objects, result containers, and context builder schemas.
Fulfills Phase 10:
- Standardized RerankResult with chunk ID, score, rank, model, and latency.
- Structured ContextBudget and AssembledContext preserving provenance, tables, and equations.
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

from backend.app.retrieval.models import ScoredChunk


class RerankInputChunk(BaseModel):
    """Candidate chunk supplied to a reranker provider."""
    chunk_id: uuid.UUID
    text: str
    retrieval_score: float = 0.0
    document_id: uuid.UUID | None = None
    page_number: int | None = None
    section_title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_scored_chunk(cls, chunk: ScoredChunk) -> RerankInputChunk:
        return cls(
            chunk_id=chunk.chunk_id,
            text=chunk.retrieval_text or chunk.content,
            retrieval_score=chunk.score,
            document_id=chunk.document_id,
            page_number=chunk.page_number,
            section_title=chunk.metadata.get("section_title"),
            metadata=chunk.metadata,
        )


class RerankResult(BaseModel):
    """Individual reranked chunk result."""
    chunk_id: uuid.UUID
    score: float
    rank: int
    model_name: str
    latency_ms: float
    text: str = ""
    document_id: uuid.UUID | None = None
    page_number: int | None = None
    section_title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextBudget(BaseModel):
    """Token budget configuration for final prompt assembly."""
    max_tokens: int = Field(default=4096, ge=64, le=128000)
    reserve_for_answer: int = Field(default=1024, ge=16)
    max_chunks: int = Field(default=10, ge=1, le=50)

    @property
    def max_context_tokens(self) -> int:
        return max(128, self.max_tokens - self.reserve_for_answer)


class AssembledCitation(BaseModel):
    """Citation provenance record bound to a context snippet."""
    citation_id: str  # e.g. "[1]"
    chunk_id: uuid.UUID
    document_id: uuid.UUID | None = None
    title: str = ""
    page_number: int | None = None
    section_title: str | None = None
    bbox: dict[str, float] | None = None
    confidence: float = 1.0


class AssembledContext(BaseModel):
    """Final LLM context assembly containing formatted text and rich provenance."""
    context_text: str
    total_tokens: int
    chunks_used_count: int
    chunks_dropped_count: int
    citations: list[AssembledCitation] = Field(default_factory=list)
    preserved_elements: dict[str, int] = Field(
        default_factory=lambda: {"tables": 0, "equations": 0, "chemical_structures": 0}
    )
