"""
Embeddings package.
Provides provider-independent text and chemistry embeddings.
"""

from backend.app.embeddings.base import (
    BaseEmbeddingProvider,
    BatchEmbeddingResult,
    EmbeddingDimensionMismatchError,
    EmbeddingError,
    EmbeddingMetadata,
    EmbeddingProviderUnavailableError,
    EmbeddingResult,
)
from backend.app.embeddings.chemical_embedder import ChemicalEmbeddingService
from backend.app.embeddings.factory import (
    get_chemical_embedding_provider,
    get_text_embedding_provider,
)
from backend.app.embeddings.providers import (
    ChemBERTaEmbeddingProvider,
    DeterministicLocalProvider,
    MorganFingerprintProvider,
    OpenAIEmbeddingProvider,
    SentenceTransformersProvider,
)
from backend.app.embeddings.text_embedder import TextEmbeddingService

__all__ = [
    "BaseEmbeddingProvider",
    "EmbeddingMetadata",
    "EmbeddingResult",
    "BatchEmbeddingResult",
    "EmbeddingError",
    "EmbeddingDimensionMismatchError",
    "EmbeddingProviderUnavailableError",
    "TextEmbeddingService",
    "ChemicalEmbeddingService",
    "get_text_embedding_provider",
    "get_chemical_embedding_provider",
    "DeterministicLocalProvider",
    "MorganFingerprintProvider",
    "SentenceTransformersProvider",
    "ChemBERTaEmbeddingProvider",
    "OpenAIEmbeddingProvider",
]
