"""
Search and Retrieval API schemas.
Provides request and response models for /api/v1/search.
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

from backend.app.reranking.models import AssembledContext
from backend.app.retrieval.models import RetrievalFilter, ScoredChunk


class SearchRequest(BaseModel):
    """Hybrid retrieval and search request."""
    query_text: str | None = Field(None, description="Natural language search query")
    query: str | None = Field(None, description="Alias for query_text")
    query_smiles: str | None = Field(None, description="Optional chemical structure SMILES")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results to return")
    filters: RetrievalFilter | None = Field(None, description="Metadata and tenant filters")
    rerank: bool = Field(default=True, description="Whether to apply cross-encoder reranking")
    rerank_pool_size: int = Field(default=50, ge=10, le=100, description="Candidate pool size for reranking")
    build_context: bool = Field(default=False, description="Whether to assemble token-budgeted prompt context")

    def get_query_str(self) -> str:
        q = (self.query_text or self.query or "").strip()
        return q


class SearchResponse(BaseModel):
    """Hybrid search results container."""
    query_text: str
    query_smiles: str | None = None
    total_results: int
    results: list[ScoredChunk]
    context: AssembledContext | None = None
    latency_ms: float
