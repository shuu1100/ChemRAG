"""
Reranking Service.
Fulfills Prompt 10.2:
- Reranks top 50–100 RRF candidate chunks using cross-encoders.
- Preserves upstream score breakdowns and outputs fine-grained cross-encoder relevance.
"""

from __future__ import annotations

from typing import Any, Sequence
import uuid

from backend.app.core.logging import get_logger
from backend.app.reranking.base import BaseRerankerProvider
from backend.app.reranking.factory import get_reranker_provider
from backend.app.reranking.models import RerankInputChunk, RerankResult
from backend.app.retrieval.models import ScoredChunk

logger = get_logger(__name__)


class RerankingService:
    """
    Coordinates candidate slicing (top 50–100) and cross-encoder inference.
    """

    def __init__(
        self,
        provider: BaseRerankerProvider | None = None,
        default_top_n: int = 10,
        default_pool_size: int = 50,
    ) -> None:
        self.provider = provider or get_reranker_provider()
        self.default_top_n = default_top_n
        self.default_pool_size = default_pool_size

    async def rerank_candidates(
        self,
        query: str,
        candidates: Sequence[ScoredChunk],
        top_n: int | None = None,
        pool_size: int | None = None,
    ) -> list[ScoredChunk]:
        """
        Rerank hybrid RRF candidates.
        Takes top `pool_size` (default 50-100) candidates and refines their order.
        """
        if not candidates or not query:
            return []

        limit_pool = pool_size or self.default_pool_size
        target_top_n = top_n or self.default_top_n

        # Slice candidate pool (top 50–100)
        pool = list(candidates)[:limit_pool]
        input_chunks = [RerankInputChunk.from_scored_chunk(c) for c in pool]
        chunk_lookup = {c.chunk_id: c for c in pool}

        # Cross-encoder inference with fallback
        try:
            rerank_results = await self.provider.rerank(
                query=query,
                chunks=input_chunks,
                top_n=target_top_n,
            )
        except Exception as exc:
            logger.warning("Reranker provider failed, falling back to RRF ordering", error=str(exc))
            return list(candidates)[:target_top_n]

        final_chunks: list[ScoredChunk] = []
        for r in rerank_results:
            orig = chunk_lookup.get(r.chunk_id)
            if not orig:
                continue

            updated_breakdown = {
                **orig.score_breakdown,
                "reranker_score": r.score,
                "reranker_rank": r.rank,
                "reranker_model": r.model_name,
                "reranker_latency_ms": r.latency_ms,
                "pre_rerank_rank": orig.rank,
                "pre_rerank_score": orig.score,
            }

            final_chunks.append(
                ScoredChunk(
                    chunk_id=orig.chunk_id,
                    document_id=orig.document_id,
                    content=orig.content,
                    raw_text=orig.raw_text,
                    retrieval_text=orig.retrieval_text,
                    display_text=orig.display_text,
                    chunk_type=orig.chunk_type,
                    chunk_index=orig.chunk_index,
                    page_number=orig.page_number,
                    bbox=orig.bbox,
                    score=r.score,
                    rank=r.rank,
                    retrieval_mode="cross_encoder_reranked",
                    score_breakdown=updated_breakdown,
                    metadata=orig.metadata,
                )
            )

        return final_chunks
