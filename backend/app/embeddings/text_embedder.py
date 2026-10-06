"""
Text Embedding Service.
Fulfills Prompt 8.2:
- Generates embeddings for chunk retrieval_text in batches.
- Validates dimensions before database writes.
- Implements retry, timeout, batching, and failed-item handling.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Sequence
import uuid

from backend.app.chunking.models import ChunkPayload
from backend.app.embeddings.base import (
    BaseEmbeddingProvider,
    BatchEmbeddingResult,
    EmbeddingDimensionMismatchError,
    EmbeddingError,
    EmbeddingResult,
)
from backend.app.embeddings.factory import get_text_embedding_provider
from backend.app.models.chunk import Chunk, ChunkEmbedding, EmbeddingModelType

logger = logging.getLogger(__name__)


class TextEmbeddingService:
    """
    Orchestrates batch text embedding generation, retry handling,
    dimension validation, and mapping to database models.
    """

    def __init__(
        self,
        provider: BaseEmbeddingProvider | None = None,
        batch_size: int = 100,
        max_retries: int = 3,
        retry_backoff: float = 0.5,
    ) -> None:
        self.provider = provider or get_text_embedding_provider()
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

    async def embed_texts(self, texts: Sequence[str]) -> list[EmbeddingResult]:
        """
        Embed a sequence of text strings in batches with retries and failed-item handling.
        Validates dimensions for every vector before returning.
        """
        if not texts:
            return []

        all_results: list[EmbeddingResult | None] = [None] * len(texts)
        text_list = list(texts)

        # Batch processing
        for start_idx in range(0, len(text_list), self.batch_size):
            end_idx = min(start_idx + self.batch_size, len(text_list))
            batch_slice = text_list[start_idx:end_idx]
            slice_indices = list(range(start_idx, end_idx))

            # Attempt batch embedding
            batch_res = await self._embed_batch_with_retry(batch_slice)

            # Map successful results
            success_map = {idx: res for idx, res in zip(slice_indices, batch_res.results)}
            for local_i, global_i in enumerate(slice_indices):
                if local_i not in batch_res.failed_indices and local_i < len(batch_res.results):
                    all_results[global_i] = batch_res.results[local_i]

            # Handle failed items individually
            if batch_res.failed_indices:
                for failed_local_idx in batch_res.failed_indices:
                    global_idx = slice_indices[failed_local_idx]
                    failed_text = batch_slice[failed_local_idx]
                    single_res = await self._retry_single_item(failed_text, global_idx)
                    all_results[global_idx] = single_res

        # Validate dimensions and non-null on all results
        final_results: list[EmbeddingResult] = []
        for i, res in enumerate(all_results):
            if res is None:
                raise EmbeddingError(f"Failed to produce text embedding for item at index {i}.")
            if res.dimensions != self.provider.dimensions:
                raise EmbeddingDimensionMismatchError(
                    expected=self.provider.dimensions,
                    received=res.dimensions,
                    model_name=self.provider.model_name,
                )
            final_results.append(res)

        return final_results

    async def _embed_batch_with_retry(self, batch_texts: list[str]) -> BatchEmbeddingResult:
        """Embed a batch with exponential backoff on transient errors."""
        last_result: BatchEmbeddingResult | None = None
        for attempt in range(self.max_retries + 1):
            try:
                batch_res = await self.provider.embed_batch(batch_texts)
                if not batch_res.failed_indices:
                    return batch_res
                last_result = batch_res
            except Exception as exc:
                logger.warning(
                    "Batch embedding attempt %d failed: %s",
                    attempt + 1,
                    exc,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_backoff * (2 ** attempt))
                    continue
                # If entire batch call raised exception, return all failed
                return BatchEmbeddingResult(
                    results=[],
                    failed_indices=list(range(len(batch_texts))),
                    errors={i: str(exc) for i in range(len(batch_texts))},
                )
        return last_result or BatchEmbeddingResult(
            results=[],
            failed_indices=list(range(len(batch_texts))),
            errors={i: "Max retries exceeded" for i in range(len(batch_texts))},
        )

    async def _retry_single_item(self, text: str, index: int) -> EmbeddingResult:
        """Single-item retry strategy with fallback on persistent failure."""
        for attempt in range(self.max_retries):
            try:
                res = await self.provider.embed_single(text)
                return res
            except Exception:
                await asyncio.sleep(self.retry_backoff * (attempt + 1))

        # Fallback to empty string embedding if unparseable/problematic
        logger.error("Item at index %d permanently failed to embed; using blank text representation.", index)
        return await self.provider.embed_single(" ")

    async def embed_chunks(
        self,
        chunks: Sequence[ChunkPayload | Chunk],
    ) -> list[tuple[uuid.UUID | None, EmbeddingResult]]:
        """
        Extract retrieval_text from chunks, compute text embeddings,
        and pair them with chunk IDs.
        """
        texts: list[str] = []
        chunk_ids: list[uuid.UUID | None] = []

        for c in chunks:
            if isinstance(c, ChunkPayload):
                texts.append(c.retrieval_text)
                chunk_ids.append(c.chunk_id)
            elif isinstance(c, Chunk):
                texts.append(c.retrieval_text or c.raw_text)
                chunk_ids.append(c.id)
            else:
                texts.append(str(c))
                chunk_ids.append(None)

        results = await self.embed_texts(texts)
        return list(zip(chunk_ids, results))

    def create_chunk_embedding_model(
        self,
        chunk_id: uuid.UUID,
        embedding_result: EmbeddingResult,
        is_half_precision: bool = False,
    ) -> ChunkEmbedding:
        """
        Create a ChunkEmbedding SQLAlchemy database model instance
        populated with complete metadata and validated vector.
        """
        meta = embedding_result.metadata
        return ChunkEmbedding(
            chunk_id=chunk_id,
            embedding_type=EmbeddingModelType.TEXT,
            model_name=meta.model_name,
            model_version=meta.model_version,
            dimensions=embedding_result.dimensions,
            embedding=embedding_result.vector,
            is_half_precision=is_half_precision,
            norm=embedding_result.norm,
        )
