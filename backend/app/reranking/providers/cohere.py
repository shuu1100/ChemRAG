"""
Hosted Cohere Cross-Encoder Reranker Provider.
Connects to Cohere rerank API with retry, backoff, and timeout controls.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Sequence
import uuid

import httpx

from backend.app.reranking.base import BaseRerankerProvider, RerankerError
from backend.app.reranking.models import RerankInputChunk, RerankResult
from backend.app.retrieval.models import ScoredChunk

logger = logging.getLogger(__name__)


class CohereRerankerProvider(BaseRerankerProvider):
    """
    Hosted cross-encoder using Cohere's /v1/rerank endpoint.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.cohere.ai",
        model_name: str = "rerank-english-v3.0",
        batch_size: int = 32,
        timeout: int = 15,
        retries: int = 2,
    ) -> None:
        super().__init__(
            model_name=model_name,
            provider_name="cohere",
            batch_size=batch_size,
            timeout=timeout,
            retries=retries,
        )
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def rerank(
        self,
        query: str,
        chunks: Sequence[RerankInputChunk | ScoredChunk],
        top_n: int | None = None,
    ) -> list[RerankResult]:
        normalized = self._normalize_inputs(chunks)
        if not normalized:
            return []

        if not self.api_key:
            raise RerankerError("Cohere API key is not configured.")

        t0 = time.perf_counter()
        documents = [c.text for c in normalized]
        limit = top_n or len(normalized)

        payload = {
            "model": self.model_name,
            "query": query,
            "documents": documents,
            "top_n": limit,
            "return_documents": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_err: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(
                        f"{self.base_url}/v1/rerank",
                        json=payload,
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        results_data = data.get("results", [])
                        elapsed_ms = (time.perf_counter() - t0) * 1000.0

                        output: list[RerankResult] = []
                        for rank, item in enumerate(results_data, start=1):
                            idx = item["index"]
                            score = float(item["relevance_score"])
                            orig = normalized[idx]
                            output.append(
                                RerankResult(
                                    chunk_id=orig.chunk_id,
                                    score=score,
                                    rank=rank,
                                    model_name=self.model_name,
                                    latency_ms=round(elapsed_ms / max(len(normalized), 1), 3),
                                    text=orig.text,
                                    document_id=orig.document_id,
                                    page_number=orig.page_number,
                                    section_title=orig.section_title,
                                    metadata=orig.metadata,
                                )
                            )
                        return output
                    elif resp.status_code in (429, 500, 502, 503, 504) and attempt < self.retries:
                        await asyncio.sleep(2 ** attempt * 0.5)
                        continue
                    else:
                        resp.raise_for_status()
            except Exception as exc:
                last_err = exc
                if attempt < self.retries:
                    await asyncio.sleep(2 ** attempt * 0.5)
                    continue

        raise RerankerError(f"Cohere rerank failed after {self.retries} attempts: {last_err}")
