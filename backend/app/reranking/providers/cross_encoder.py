"""
Local Cross-Encoder Provider using SentenceTransformers.
Supports BAAI/bge-reranker-large, cross-encoder/ms-marco-MiniLM-L-6-v2, etc.,
with graceful fallback to DeterministicRerankerProvider.
"""

from __future__ import annotations

import logging
from pathlib import Path
import time
from typing import Any, Sequence
import uuid

from backend.app.reranking.base import BaseRerankerProvider
from backend.app.reranking.models import RerankInputChunk, RerankResult
from backend.app.reranking.providers.deterministic import DeterministicRerankerProvider
from backend.app.retrieval.models import ScoredChunk

logger = logging.getLogger(__name__)


class LocalCrossEncoderProvider(BaseRerankerProvider):
    """
    Local neural cross-encoder running via sentence-transformers.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-large",
        batch_size: int = 32,
    ) -> None:
        super().__init__(
            model_name=model_name,
            provider_name="cross-encoder",
            batch_size=batch_size,
        )
        self._model = None
        self._model_loaded = False
        self._fallback = DeterministicRerankerProvider(
            model_name=f"{model_name}-fallback",
            batch_size=batch_size,
        )

    def _try_load_model(self) -> bool:
        if self._model_loaded:
            return True
        if not Path(self.model_name).exists():
            return False
        try:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.model_name, max_length=512)
            self._model_loaded = True
            return True
        except Exception as exc:
            logger.info("Local CrossEncoder weights not found: %s", exc)
            return False

    async def rerank(
        self,
        query: str,
        chunks: Sequence[RerankInputChunk | ScoredChunk],
        top_n: int | None = None,
    ) -> list[RerankResult]:
        normalized = self._normalize_inputs(chunks)
        if not normalized:
            return []

        if not self._try_load_model():
            return await self._fallback.rerank(query, normalized, top_n)

        t0 = time.perf_counter()
        pairs = [[query, c.text] for c in normalized]
        scores = self._model.predict(pairs, batch_size=self.batch_size)

        scored_items = list(zip(scores, normalized))
        scored_items.sort(
            key=lambda x: (-float(x[0]), -x[1].retrieval_score, str(x[1].chunk_id))
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        limit = top_n or len(scored_items)

        results: list[RerankResult] = []
        for rank, (score, chunk) in enumerate(scored_items[:limit], start=1):
            results.append(
                RerankResult(
                    chunk_id=chunk.chunk_id,
                    score=float(score),
                    rank=rank,
                    model_name=self.model_name,
                    latency_ms=round(elapsed_ms / max(len(normalized), 1), 3),
                    text=chunk.text,
                    document_id=chunk.document_id,
                    page_number=chunk.page_number,
                    section_title=chunk.section_title,
                    metadata=chunk.metadata,
                )
            )

        return results
