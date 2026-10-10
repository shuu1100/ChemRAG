"""
Retrieval data models, filters, and query transfer objects.
Fulfills Phase 09 requirements:
- Flexible multi-modal query representation.
- Comprehensive metadata filters (tenant, document, section, date, chemical).
- Detailed scored chunk representation with score breakdowns and provenance.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from backend.app.models.chunk import ChunkType


class RetrievalFilter(BaseModel):
    """
    Metadata filter criteria applied across semantic, lexical, and chemical retrievers.
    Guarantees tenant isolation and selective query scoping.
    """
    organization_id: uuid.UUID | None = None
    document_ids: list[uuid.UUID] | None = None
    section_ids: list[uuid.UUID] | None = None
    chunk_types: list[ChunkType] | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    contains_chemical_entities: bool | None = None
    chemical_entity_ids: list[uuid.UUID] | None = None
    cas_number: str | None = None
    inchikey: str | None = None
    smiles: str | None = None


class ScoredChunk(BaseModel):
    """
    Result chunk returned by any retrieval engine, populated with
    score breakdowns, ranks, and citation provenance.
    """
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str | None = None
    content: str
    raw_text: str = ""
    retrieval_text: str = ""
    display_text: str = ""
    chunk_type: ChunkType | None = ChunkType.TEXT
    chunk_index: int | None = 0
    page_number: int | None = None
    bbox: dict[str, float] | None = None
    score: float = 0.0
    rank: int = 1
    retrieval_mode: str = "semantic"
    score_breakdown: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalQueryPayload(BaseModel):
    """
    Complete configuration for hybrid retrieval execution.
    """
    query_text: str
    query_smiles: str | None = None
    top_k: int = Field(default=10, ge=1, le=100)
    filters: RetrievalFilter | None = None
    rrf_k: int = Field(default=60, ge=1, le=1000)
    semantic_weight: float = Field(default=1.0, ge=0.0)
    lexical_weight: float = Field(default=1.0, ge=0.0)
    chemical_weight: float = Field(default=1.0, ge=0.0)
    ef_search: int = Field(default=100, ge=10, le=1000)
