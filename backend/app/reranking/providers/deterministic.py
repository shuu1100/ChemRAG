"""
Deterministic Reranker Provider.
Provides reproducible, fast cross-encoder relevance scoring for CI/CD,
offline environments, and baseline benchmarks.
"""

from __future__ import annotations

import math
import re
import time
from typing import Any, Sequence
import uuid

from backend.app.reranking.base import BaseRerankerProvider
from backend.app.reranking.models import RerankInputChunk, RerankResult
from backend.app.retrieval.models import ScoredChunk

CAS_PATTERN = re.compile(r"\b\d{2,7}-\d{2}-\d\b")
FORMULA_PATTERN = re.compile(r"\b(?:[A-Z][a-z]?\d*){2,}\b")


class DeterministicRerankerProvider(BaseRerankerProvider):
    """
    Local deterministic cross-encoder simulator.
    Evaluates lexical-semantic interaction, exact identifier alignment,
    and phrase coherence to generate fine-grained relevance scores in [0.0, 1.0].
    """

    def __init__(
        self,
        model_name: str = "chemrag-deterministic-cross-encoder-v1",
        batch_size: int = 32,
    ) -> None:
        super().__init__(
            model_name=model_name,
            provider_name="local-deterministic",
            batch_size=batch_size,
        )

    def _score_pair(self, query: str, text: str) -> float:
        """Compute fine-grained relevance score between query and candidate text."""
        q_lower = query.lower()
        t_lower = text.lower()

        q_tokens = set(re.findall(r"\w+", q_lower))
        t_tokens = set(re.findall(r"\w+", t_lower))

        if not q_tokens:
            return 0.0

        # 1. Token overlap recall and precision
        overlap = q_tokens.intersection(t_tokens)
        recall = len(overlap) / len(q_tokens)
        jaccard = len(overlap) / max(len(q_tokens.union(t_tokens)), 1)

        score = 0.5 * recall + 0.3 * jaccard

        # 2. Exact phrase bonus
        if q_lower in t_lower:
            score += 0.2

        # 3. Chemical / CAS technical identifier exact match bonus
        q_cas = CAS_PATTERN.findall(query)
        for cas in q_cas:
            if cas in text:
                score += 0.4

        q_formulas = FORMULA_PATTERN.findall(query)
        for f in q_formulas:
            if f in text:
                score += 0.25

        # Normalize via sigmoid to (0, 1)
        # S(x) = 1 / (1 + exp(-2 * (score - 0.5)))
        calibrated = 1.0 / (1.0 + math.exp(-2.5 * (score - 0.5)))
        return round(float(calibrated), 4)

    async def rerank(
        self,
        query: str,
        chunks: Sequence[RerankInputChunk | ScoredChunk],
        top_n: int | None = None,
    ) -> list[RerankResult]:
        t0 = time.perf_counter()
        normalized = self._normalize_inputs(chunks)
        if not normalized:
            return []

        scored_items: list[tuple[float, RerankInputChunk]] = []
        for c in normalized:
            s = self._score_pair(query, c.text)
            scored_items.append((s, c))

        # Deterministic sort: descending score, then retrieval_score, then chunk_id string
        scored_items.sort(
            key=lambda x: (-x[0], -x[1].retrieval_score, str(x[1].chunk_id))
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        limit = top_n or len(scored_items)

        results: list[RerankResult] = []
        for rank, (score, chunk) in enumerate(scored_items[:limit], start=1):
            results.append(
                RerankResult(
                    chunk_id=chunk.chunk_id,
                    score=score,
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
