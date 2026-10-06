"""
ChemRAG — Chemical-Aware Chunking Package
==========================================
Protects SMILES, InChI, formulas, equations, and SOP steps during semantic chunking.
"""
from __future__ import annotations

from backend.app.chunking.atomic_units import AtomicUnitGuard
from backend.app.chunking.chemical_chunker import (
    ChemicalAwareChunker,
    estimate_token_count,
)
from backend.app.chunking.models import ChunkPayload

__all__ = [
    "AtomicUnitGuard",
    "ChemicalAwareChunker",
    "ChunkPayload",
    "estimate_token_count",
]
