"""
ChemRAG — Chemical-Aware Chunking Data Structures
=================================================
Structured representation for retrieval chunks.
Maintains raw_text, retrieval_text, and display_text separately.
Preserves spatial bounding box coordinates for source traceability.
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from backend.app.models.chunk import ChunkType
from backend.app.parsing.models import BoundingBox


@dataclass
class ChunkPayload:
    """
    Complete chunk object containing distinct raw, retrieval, and display representations,
    along with spatial geometry and chemical entity identifiers.
    """
    chunk_id: uuid.UUID = field(default_factory=uuid.uuid4)
    document_id: Optional[uuid.UUID] = None
    version_id: Optional[uuid.UUID] = None
    page_number: int = 1
    chunk_index: int = 0
    chunk_type: ChunkType = ChunkType.TEXT

    # Distinct representations (Prompt 7.3)
    raw_text: str = ""          # Exact source text untouched
    retrieval_text: str = ""    # Contextually enriched for dense/sparse vector search
    display_text: str = ""      # Clean formatted rendering for UI and LLM synthesis

    # Provenance and geometry (Prompt 7.2 & Exit Criteria)
    bbox: Optional[BoundingBox] = None
    char_start: int = 0
    char_end: int = 0

    # Hierarchical context
    section_title: Optional[str] = None
    subsection_title: Optional[str] = None

    # Chemical & asset tracking
    chemical_entities: List[str] = field(default_factory=list)  # Mentioned names, formulas, InChIKeys
    asset_ids: List[str] = field(default_factory=list)          # Tables, figures, equations referenced

    # Engine metadata
    chunker_name: str = "ChemicalAwareChunker"
    chunker_version: str = "1.0.0"
    confidence: float = 1.0
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def contains_chemical_entities(self) -> bool:
        """Returns True if chunk contains extracted chemical entities."""
        return len(self.chemical_entities) > 0

    @property
    def content_hash(self) -> str:
        """SHA-256 hash of the raw text for integrity and deduplication."""
        return hashlib.sha256(self.raw_text.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary for database persistence or serialization."""
        return {
            "chunk_id": str(self.chunk_id),
            "document_id": str(self.document_id) if self.document_id else None,
            "version_id": str(self.version_id) if self.version_id else None,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "chunk_type": self.chunk_type.value,
            "raw_text": self.raw_text,
            "retrieval_text": self.retrieval_text,
            "display_text": self.display_text,
            "bbox": self.bbox.to_dict() if self.bbox else None,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "section_title": self.section_title,
            "subsection_title": self.subsection_title,
            "chemical_entities": self.chemical_entities,
            "asset_ids": self.asset_ids,
            "chunker_name": self.chunker_name,
            "chunker_version": self.chunker_version,
            "confidence": self.confidence,
            "token_count": self.token_count,
            "content_hash": self.content_hash,
            "metadata": self.metadata,
        }
