"""
Provider-agnostic embedding factory.
Fulfills Prompt 8.1:
- Instantiates text and chemical embedding providers based on system configuration.
- Decouples downstream services from concrete provider implementations.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.core.config import EmbeddingProvider, get_settings
from backend.app.embeddings.base import BaseEmbeddingProvider
from backend.app.embeddings.providers.chemberta import ChemBERTaEmbeddingProvider
from backend.app.embeddings.providers.deterministic import DeterministicLocalProvider
from backend.app.embeddings.providers.morgan import MorganFingerprintProvider
from backend.app.embeddings.providers.openai import OpenAIEmbeddingProvider
from backend.app.embeddings.providers.sentence_transformers import (
    SentenceTransformersProvider,
)
from backend.app.models.chunk import EmbeddingModelType

logger = logging.getLogger(__name__)


def get_text_embedding_provider(
    provider_type: EmbeddingProvider | str | None = None,
    dimensions: int | None = None,
    model_name: str | None = None,
    **kwargs: Any,
) -> BaseEmbeddingProvider:
    """
    Factory creating a provider-independent text embedding provider.
    """
    settings = get_settings()
    emb_cfg = settings.embeddings

    chosen_provider = provider_type or emb_cfg.provider
    if isinstance(chosen_provider, str):
        try:
            chosen_provider = EmbeddingProvider(chosen_provider)
        except ValueError:
            chosen_provider = EmbeddingProvider.LOCAL

    target_dims = dimensions or emb_cfg.dimensions
    target_model = model_name or emb_cfg.model

    if chosen_provider == EmbeddingProvider.OPENAI:
        api_key_str = emb_cfg.api_key.get_secret_value() if emb_cfg.api_key else None
        if not api_key_str or "replace-with" in api_key_str or "placeholder" in api_key_str or not api_key_str.startswith("sk-"):
            logger.info("OpenAI API key not set or placeholder; using deterministic local embedding provider.")
            return DeterministicLocalProvider(
                model_name=target_model,
                dimensions=target_dims,
                embedding_type=EmbeddingModelType.TEXT,
                is_normalized=True,
            )
        return OpenAIEmbeddingProvider(
            api_key=api_key_str,
            base_url=emb_cfg.base_url,
            model_name=target_model,
            dimensions=target_dims,
            batch_size=emb_cfg.batch_size,
            timeout=emb_cfg.timeout,
            retries=emb_cfg.retries,
        )

    elif chosen_provider == EmbeddingProvider.SENTENCE_TRANSFORMERS:
        return SentenceTransformersProvider(
            model_name=target_model,
            dimensions=target_dims,
            batch_size=emb_cfg.batch_size,
            timeout=emb_cfg.timeout,
            retries=emb_cfg.retries,
        )

    else:
        # Default local deterministic
        return DeterministicLocalProvider(
            model_name=target_model,
            dimensions=target_dims,
            embedding_type=EmbeddingModelType.TEXT,
            is_normalized=True,
            batch_size=emb_cfg.batch_size,
        )


def get_chemical_embedding_provider(
    provider_type: str | None = None,
    dimensions: int | None = None,
    model_name: str | None = None,
    **kwargs: Any,
) -> BaseEmbeddingProvider:
    """
    Factory creating a provider-independent chemical embedding provider.
    Fulfills Prompt 8.3:
    Provides molecular embedding models such as ChemBERTa or Morgan circular fingerprints.
    """
    settings = get_settings()
    emb_cfg = settings.embeddings

    target_dims = dimensions or emb_cfg.chemical_dimensions
    target_model = model_name or emb_cfg.chemical_model
    ptype = (provider_type or "rdkit-morgan").lower()

    if "chemberta" in ptype:
        return ChemBERTaEmbeddingProvider(
            model_name=target_model,
            dimensions=target_dims,
            batch_size=kwargs.get("batch_size", 64),
        )
    elif "morgan" in ptype or "rdkit" in ptype:
        return MorganFingerprintProvider(
            dimensions=target_dims,
            model_name=target_model or "rdkit-morgan-ecfp4",
            radius=kwargs.get("radius", 2),
            batch_size=kwargs.get("batch_size", 100),
        )
    else:
        return DeterministicLocalProvider(
            model_name=target_model,
            dimensions=target_dims,
            embedding_type=EmbeddingModelType.CHEMICAL,
            is_normalized=True,
        )
