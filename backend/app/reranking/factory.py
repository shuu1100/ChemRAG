"""
Reranker provider factory.
Fulfills Prompt 10.1:
- Instantiates cross-encoder providers based on configuration.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.core.config import RerankerProvider, get_settings
from backend.app.reranking.base import BaseRerankerProvider
from backend.app.reranking.providers.cohere import CohereRerankerProvider
from backend.app.reranking.providers.cross_encoder import LocalCrossEncoderProvider
from backend.app.reranking.providers.deterministic import (
    DeterministicRerankerProvider,
)

logger = logging.getLogger(__name__)


def get_reranker_provider(
    provider_type: RerankerProvider | str | None = None,
    model_name: str | None = None,
    **kwargs: Any,
) -> BaseRerankerProvider:
    """
    Factory creating a provider-independent cross-encoder reranker.
    """
    settings = get_settings()
    rcfg = settings.reranker

    chosen = provider_type or rcfg.provider
    if isinstance(chosen, str):
        try:
            chosen = RerankerProvider(chosen)
        except ValueError:
            chosen = RerankerProvider.LOCAL

    model = model_name or rcfg.model

    if chosen == RerankerProvider.COHERE:
        api_key_str = rcfg.api_key.get_secret_value() if rcfg.api_key else None
        if not api_key_str:
            logger.info("Cohere API key not set; using local deterministic cross-encoder.")
            return DeterministicRerankerProvider(
                model_name=model,
                batch_size=rcfg.batch_size,
            )
        return CohereRerankerProvider(
            api_key=api_key_str,
            base_url=rcfg.base_url,
            model_name=model,
            batch_size=rcfg.batch_size,
            timeout=rcfg.timeout,
            retries=rcfg.retries,
        )

    elif chosen in (RerankerProvider.CROSS_ENCODER, RerankerProvider.BGE):
        return LocalCrossEncoderProvider(
            model_name=model,
            batch_size=rcfg.batch_size,
        )

    else:
        # Default local deterministic
        return DeterministicRerankerProvider(
            model_name=model,
            batch_size=rcfg.batch_size,
        )
