"""
OpenAI & Hosted REST Embedding Provider.
Supports OpenAI text-embedding-3-large, text-embedding-3-small,
as well as OpenAI-compatible REST endpoints (e.g. Voyage, vLLM, LiteLLM, Ollama).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from backend.app.embeddings.base import (
    BaseEmbeddingProvider,
    BatchEmbeddingResult,
    EmbeddingError,
    EmbeddingMetadata,
    EmbeddingProviderUnavailableError,
    EmbeddingResult,
)
from backend.app.models.chunk import EmbeddingModelType

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """
    Hosted embedding provider using OpenAI-compatible REST API.
    Implements exponential backoff retries, request timeouts, and batching.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        model_name: str = "text-embedding-3-large",
        dimensions: int = 3072,
        is_normalized: bool = True,
        batch_size: int = 100,
        timeout: int = 30,
        retries: int = 3,
    ) -> None:
        super().__init__(
            model_name=model_name,
            dimensions=dimensions,
            provider_name="openai",
            embedding_type=EmbeddingModelType.TEXT,
            model_version="3.0",
            is_normalized=is_normalized,
            batch_size=batch_size,
            timeout=timeout,
            retries=retries,
        )
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def _post_embeddings_request(self, texts: list[str]) -> list[dict[str, Any]]:
        """Execute HTTP request to /embeddings endpoint with retry and backoff."""
        if not self.api_key:
            raise EmbeddingProviderUnavailableError("OpenAI API key is missing or not configured.")

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": texts,
            "model": self.model_name,
            "dimensions": self.dimensions,
        }

        last_err: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        return data.get("data", [])
                    elif resp.status_code in (401, 403):
                        raise EmbeddingProviderUnavailableError(f"OpenAI API key unauthorized (status {resp.status_code}).")
                    elif resp.status_code in (429, 500, 502, 503, 504) and attempt < self.retries:
                        await asyncio.sleep(2 ** attempt * 0.5)
                        continue
                    else:
                        raise EmbeddingProviderUnavailableError(f"OpenAI embedding request failed with HTTP {resp.status_code}.")
            except EmbeddingProviderUnavailableError:
                raise
            except httpx.HTTPStatusError as http_err:
                raise EmbeddingProviderUnavailableError(f"OpenAI HTTP error: {http_err}") from http_err
            except Exception as exc:
                last_err = exc
                if attempt < self.retries:
                    await asyncio.sleep(2 ** attempt * 0.5)
                    continue
                break

        raise EmbeddingError(f"OpenAI embedding request failed after {self.retries} retries: {last_err}")

    async def embed_batch(self, texts: list[str]) -> BatchEmbeddingResult:
        results: list[EmbeddingResult] = []
        failed_indices: list[int] = []
        errors: dict[int, str] = {}
        metadata = self.get_metadata()

        try:
            data_items = await self._post_embeddings_request(texts)
            for idx, item in enumerate(data_items):
                try:
                    vec = item["embedding"]
                    norm_vec, norm = self.validate_vector(vec)
                    results.append(
                        EmbeddingResult(
                            vector=norm_vec,
                            dimensions=self.dimensions,
                            norm=norm,
                            metadata=metadata,
                        )
                    )
                except Exception as val_exc:
                    failed_indices.append(idx)
                    errors[idx] = str(val_exc)
        except EmbeddingProviderUnavailableError:
            raise
        except Exception as exc:
            # Mark all as failed if whole batch call failed
            for idx in range(len(texts)):
                failed_indices.append(idx)
                errors[idx] = str(exc)

        return BatchEmbeddingResult(
            results=results,
            failed_indices=failed_indices,
            errors=errors,
        )
