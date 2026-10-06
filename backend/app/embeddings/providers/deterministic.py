"""
Deterministic local embedding provider.
Provides reproducible, fast, zero-dependency unit-norm vector embeddings
for offline testing, development, and fallback scenarios.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any

from backend.app.embeddings.base import (
    BaseEmbeddingProvider,
    BatchEmbeddingResult,
    EmbeddingMetadata,
    EmbeddingResult,
)
from backend.app.models.chunk import EmbeddingModelType


class DeterministicLocalProvider(BaseEmbeddingProvider):
    """
    Local embedding provider generating deterministic, unit-normalized vectors.
    Reproducibility guarantee:
    Given the same (text, model_name, dimensions), this provider will always
    produce the exact identical vector with float-level precision.
    """

    def __init__(
        self,
        model_name: str = "deterministic-local-v1",
        dimensions: int = 3072,
        embedding_type: EmbeddingModelType = EmbeddingModelType.TEXT,
        is_normalized: bool = True,
        batch_size: int = 100,
    ) -> None:
        super().__init__(
            model_name=model_name,
            dimensions=dimensions,
            provider_name="local-deterministic",
            embedding_type=embedding_type,
            model_version="1.0.0",
            is_normalized=is_normalized,
            batch_size=batch_size,
        )

    def _generate_vector(self, text: str) -> list[float]:
        """
        Generate a deterministic pseudorandom projection vector from text.
        Uses SHA-256 with multiple salt iterations to project across all dimensions.
        """
        if not text:
            # Consistent vector for empty string
            text = "__EMPTY__"

        raw_values: list[float] = []
        seed_bytes = text.encode("utf-8")

        # Generate enough bytes for all dimensions (4 bytes float per dimension)
        chunk_idx = 0
        while len(raw_values) < self.dimensions:
            salt = f":salt_{chunk_idx}".encode("ascii")
            digest = hashlib.sha256(seed_bytes + salt).digest()
            # Unpack 8 32-bit ints from the 32-byte digest
            for i in range(0, 32, 4):
                val_int = int.from_bytes(digest[i : i + 4], byteorder="big", signed=True)
                # Normalize integer to range [-1.0, 1.0]
                val_float = val_int / 2147483648.0
                raw_values.append(val_float)
                if len(raw_values) == self.dimensions:
                    break
            chunk_idx += 1

        return raw_values

    async def embed_batch(self, texts: list[str]) -> BatchEmbeddingResult:
        results: list[EmbeddingResult] = []
        failed_indices: list[int] = []
        errors: dict[int, str] = dict()

        metadata = self.get_metadata()

        for idx, text in enumerate(texts):
            try:
                raw_vec = self._generate_vector(text)
                norm_vec, norm = self.validate_vector(raw_vec)
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
