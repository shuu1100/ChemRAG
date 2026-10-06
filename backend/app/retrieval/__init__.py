"""
Retrieval package.
Provides semantic, lexical, chemical, filtered, and hybrid RRF retrieval.
"""

from backend.app.retrieval.chemical import ChemicalRetriever
from backend.app.retrieval.filtered_ann import FilteredANNScanner, ScanOrderMode
from backend.app.retrieval.fusion import ReciprocalRankFusion
from backend.app.retrieval.hybrid import HybridRetrievalService
from backend.app.retrieval.lexical import BaseLexicalRetriever, PostgreSQLLexicalRetriever
from backend.app.retrieval.models import (
    RetrievalFilter,
    RetrievalQueryPayload,
    ScoredChunk,
)
from backend.app.retrieval.semantic import SemanticRetriever

__all__ = [
    "RetrievalFilter",
    "ScoredChunk",
    "RetrievalQueryPayload",
    "SemanticRetriever",
    "BaseLexicalRetriever",
    "PostgreSQLLexicalRetriever",
    "ChemicalRetriever",
    "ReciprocalRankFusion",
    "HybridRetrievalService",
    "FilteredANNScanner",
    "ScanOrderMode",
]
