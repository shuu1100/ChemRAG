"""
Reranking package.
Provides cross-encoder candidate refinement and provenance-preserving context construction.
"""

from backend.app.reranking.base import BaseRerankerProvider, RerankerError
from backend.app.reranking.context_builder import ContextBuilder, estimate_tokens
from backend.app.reranking.factory import get_reranker_provider
from backend.app.reranking.models import (
    AssembledCitation,
    AssembledContext,
    ContextBudget,
    RerankInputChunk,
    RerankResult,
)
from backend.app.reranking.providers import (
    CohereRerankerProvider,
    DeterministicRerankerProvider,
    LocalCrossEncoderProvider,
)
from backend.app.reranking.service import RerankingService

__all__ = [
    "BaseRerankerProvider",
    "RerankerError",
    "RerankInputChunk",
    "RerankResult",
    "ContextBudget",
    "AssembledCitation",
    "AssembledContext",
    "DeterministicRerankerProvider",
    "LocalCrossEncoderProvider",
    "CohereRerankerProvider",
    "get_reranker_provider",
    "RerankingService",
    "ContextBuilder",
    "estimate_tokens",
]
