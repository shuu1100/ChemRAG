"""
Sentence Transformers Embedding Provider.
Supports local text embedding models such as BAAI/bge-large-en-v1.5,
all-MiniLM-L6-v2, and domain-adapted text encoders.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.embeddings.base import (
    BaseEmbeddingProvider,
    BatchEmbeddingResult,
    EmbeddingMetadata,
    EmbeddingResult,
)
from backend.app.embeddings.providers.deterministic import DeterministicLocalProvider
from backend.app.models.chunk import EmbeddingModelType

logger = logging.getLogger(__name__)


class SentenceTransformersProvider(BaseEmbeddingProvider):
    """
    Local embedding provider utilizing the sentence-transformers library.
    Falls back gracefully to deterministic local embeddings when weights
    are unavailable or offline.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        dimensions: int = 3072,
        is_normalized: bool = True,
        batch_size: int = 64,
        timeout: int = 30,
        retries: int = 3,
    ) -> None:
        super().__init__(
            model_name=model_name,
            dimensions=dimensions,
            provider_name="sentence-transformers",
            embedding_type=EmbeddingModelType.TEXT,
            model_version="2.0.0",
            is_normalized=is_normalized,
            batch_size=batch_size,
            timeout=timeout,
            retries=retries,
        )
        self._model: Any = None
        self._model_loaded = False
        self._fallback_provider = DeterministicLocalProvider(
            model_name=f"{model_name}-fallback",
            dimensions=dimensions,
            embedding_type=EmbeddingModelType.TEXT,
            is_normalized=is_normalized,
            batch_size=batch_size,
        )

    def _try_load_model(self) -> bool:
        if self._model_loaded and self._model is not None:
            return True
        from pathlib import Path
        if not Path(self.model_name).exists():
            return False
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, local_files_only=True)
            self._model_loaded = True
            return True
        except Exception as exc:
            logger.info("SentenceTransformer model not available in local cache: %s", exc)
            return False

    async def embed_batch(self, texts: list[str]) -> BatchEmbeddingResult:
        if not self._try_load_model() or self._model is None:
            res = await self._fallback_provider.embed_batch(texts)
            updated_results = []
            meta = self.get_metadata()
            for r in res.results:
                updated_results.append(
                    EmbeddingResult(
                        vector=r.vector,
                        dimensions=r.dimensions,
                        norm=r.norm,
                        metadata=meta,
                        tokens_used=r.tokens_used,
                    )
                )
            return BatchEmbeddingResult(
                results=updated_results,
                failed_indices=res.failed_indices,
                errors=res.errors,
            )

        results: list[EmbeddingResult] = []
        failed_indices: list[int] = []
        errors: dict[int, str] = {}
        metadata = self.get_metadata()

        for idx, text in enumerate(texts):
            try:
                emb = self._model.encode(text, normalize_embeddings=False)
                vec = emb.tolist() if hasattr(emb, "tolist") else list(emb)
                # Pad or project if dimensionality differs from configured target
                if len(vec) < self.dimensions:
                    vec = vec + [0.0] * (self.dimensions - len(vec))
                elif len(vec) > self.dimensions:
                    vec = vec[: self.dimensions]

                norm_vec, norm = self.validate_vector(vec)
                results.append(
                    EmbeddingResult(
                        vector=norm_vec,
                        dimensions=self.dimensions,
                        norm=norm,
                        metadata=metadata,
                        tokens_used=len(text.split()),
                    )
                )
            except Exception as exc:
                failed_indices.append(idx)
                errors[idx] = str(exc)

        return BatchEmbeddingResult(
            results=results,
            failed_indices=failed_indices,
            errors=errors,
        )
