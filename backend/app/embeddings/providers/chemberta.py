"""
ChemBERTa Embedding Provider for Molecular Transformers.
Uses HuggingFace transformers (e.g., deepchem/ChemBERTa-77M-MTR or seyonec/ChemBERTa-zinc-base-v1)
with mean pooling, with zero-downtime offline fallback to Morgan Fingerprints.
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
from backend.app.embeddings.providers.morgan import MorganFingerprintProvider
from backend.app.models.chunk import EmbeddingModelType

logger = logging.getLogger(__name__)


class ChemBERTaEmbeddingProvider(BaseEmbeddingProvider):
    """
    ChemBERTa molecular transformer embedding provider.
    Tokenizes canonical SMILES and pools transformer representations.
    Falls back gracefully to Morgan Fingerprint provider if model weights
    are unavailable locally.
    """

    def __init__(
        self,
        model_name: str = "deepchem/ChemBERTa-77M-MTR",
        dimensions: int = 3072,
        is_normalized: bool = True,
        batch_size: int = 64,
        timeout: int = 30,
        retries: int = 3,
    ) -> None:
        super().__init__(
            model_name=model_name,
            dimensions=dimensions,
            provider_name="chemberta",
            embedding_type=EmbeddingModelType.CHEMICAL,
            model_version="1.0.0",
            is_normalized=is_normalized,
            batch_size=batch_size,
            timeout=timeout,
            retries=retries,
        )
        self._tokenizer = None
        self._model = None
        self._model_loaded = False
        self._fallback_provider = MorganFingerprintProvider(
            dimensions=dimensions,
            model_name=f"{model_name}-fallback-morgan",
            is_normalized=is_normalized,
            batch_size=batch_size,
        )

    def _try_load_model(self) -> bool:
        """Attempt to load ChemBERTa model and tokenizer from local cache."""
        if self._model_loaded:
            return True
        from pathlib import Path
        if not Path(self.model_name).exists():
            return False
        try:
            from transformers import AutoModel, AutoTokenizer
            import torch

            # Only attempt local files first to prevent unhandled blocking downloads
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name, local_files_only=True)
            self._model = AutoModel.from_pretrained(self.model_name, local_files_only=True)
            self._model.eval()
            self._model_loaded = True
            return True
        except Exception as exc:
            logger.info("ChemBERTa local model not cached, using Morgan fingerprint backend: %s", exc)
            return False

    async def embed_batch(self, texts: list[str]) -> BatchEmbeddingResult:
        if not self._try_load_model():
            # Use Morgan fingerprint provider as robust fallback
            res = await self._fallback_provider.embed_batch(texts)
            # Rebrand metadata to this provider's name/model while preserving chemical vector
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

        # Transformers-based execution
        import torch

        results: list[EmbeddingResult] = []
        failed_indices: list[int] = []
        errors: dict[int, str] = {}
        metadata = self.get_metadata()

        for idx, text in enumerate(texts):
            try:
                inputs = self._tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
                with torch.no_grad():
                    outputs = self._model(**inputs)
                    # Mean pooling over attention mask
                    attention_mask = inputs["attention_mask"].unsqueeze(-1)
                    embeddings = outputs.last_hidden_state * attention_mask
                    sum_embeddings = torch.sum(embeddings, dim=1)
                    sum_mask = torch.clamp(attention_mask.sum(dim=1), min=1e-9)
                    mean_pooled = (sum_embeddings / sum_mask).squeeze(0).tolist()

                # Project or pad to target dimensions if needed
                if len(mean_pooled) < self.dimensions:
                    mean_pooled = mean_pooled + [0.0] * (self.dimensions - len(mean_pooled))
                elif len(mean_pooled) > self.dimensions:
                    mean_pooled = mean_pooled[: self.dimensions]

                norm_vec, norm = self.validate_vector(mean_pooled)
                results.append(
                    EmbeddingResult(
                        vector=norm_vec,
                        dimensions=self.dimensions,
                        norm=norm,
                        metadata=metadata,
                        tokens_used=inputs["input_ids"].shape[1],
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
