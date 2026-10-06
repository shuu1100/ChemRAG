"""
Base Reranker Provider Interface.
Fulfills Prompt 10.1:
- Provider-independent cross-encoder interface supporting local and hosted models.
- Standardized inputs (query + candidate chunks) and outputs (chunk ID, score, rank, model, latency).
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Sequence
import uuid

from backend.app.reranking.models import RerankInputChunk, RerankResult
from backend.app.retrieval.models import ScoredChunk


class RerankerError(Exception):
    """Base exception for reranking errors."""
    pass


class BaseRerankerProvider(ABC):
    """
    Abstract interface for cross-encoder rerankers.
    The caller receives normalized RerankResult instances regardless of provider.
    """

    def __init__(
        self,
        model_name: str,
        provider_name: str,
        batch_size: int = 32,
        timeout: int = 15,
        retries: int = 2,
    ) -> None:
        self.model_name = model_name
        self.provider_name = provider_name
        self.batch_size = batch_size
        self.timeout = timeout
        self.retries = retries

    def _normalize_inputs(
        self,
        chunks: Sequence[RerankInputChunk | ScoredChunk],
    ) -> list[RerankInputChunk]:
        """Convert heterogeneous chunk inputs into standard RerankInputChunk instances."""
        normalized: list[RerankInputChunk] = []
        for c in chunks:
            if isinstance(c, ScoredChunk):
                normalized.append(RerankInputChunk.from_scored_chunk(c))
            elif isinstance(c, RerankInputChunk):
                normalized.append(c)
            else:
                raise TypeError(f"Unsupported chunk type for reranking: {type(c)}")
        return normalized

    @abstractmethod
    async def rerank(
        self,
        query: str,
        chunks: Sequence[RerankInputChunk | ScoredChunk],
        top_n: int | None = None,
    ) -> list[RerankResult]:
        """
        Score and rank candidate chunks against the query using a cross-encoder.
        Returns sorted list of RerankResult ordered by descending score.
        """
        pass

    def rerank_sync(
        self,
        query: str,
        chunks: Sequence[RerankInputChunk | ScoredChunk],
        top_n: int | None = None,
    ) -> list[RerankResult]:
        """Synchronous convenience wrapper."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import nest_asyncio  # type: ignore[import-untyped]
            nest_asyncio.apply()
            return loop.run_until_complete(self.rerank(query, chunks, top_n))
        return asyncio.run(self.rerank(query, chunks, top_n))
