"""
ChemRAG — Chunk & Provenance Models
=====================================
Covers: chunks, chunk_embeddings, provenance
"""
from __future__ import annotations

import uuid
import enum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean, Enum as SAEnum, Float, ForeignKey,
    Index, Integer, SmallInteger, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import TYPE_CHECKING

from backend.app.db.base import Base
from backend.app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.document import Document, DocumentPage, DocumentSection
    from backend.app.models.chemical import ChunkChemicalEntity


# ─────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────


class ChunkType(str, enum.Enum):
    TEXT = "text"
    TABLE = "table"
    FIGURE_CAPTION = "figure_caption"
    EQUATION = "equation"
    CHEMICAL = "chemical"
    MIXED = "mixed"


class EmbeddingModelType(str, enum.Enum):
    TEXT = "text"
    CHEMICAL = "chemical"
    IMAGE = "image"
    MULTIMODAL = "multimodal"


class ProvenanceObjectType(str, enum.Enum):
    TEXT = "text"
    TABLE = "table"
    EQUATION = "equation"
    CHEMICAL_STRUCTURE = "chemical_structure"
    IMAGE = "image"
    CHUNK = "chunk"
    CITATION = "citation"


# ─────────────────────────────────────────────────────────
# Provenance (Prompt 2.2)
# ─────────────────────────────────────────────────────────


class Provenance(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Universal provenance record linking any extracted object back to its
    exact origin: document → version → page → bounding box → char offsets.

    Supports: text, tables, equations, chemical structures, images, chunks, citations.
    """
    __tablename__ = "provenance"

    # ── What object does this describe? ─────────────────────
    object_type: Mapped[ProvenanceObjectType] = mapped_column(
        SAEnum(ProvenanceObjectType, name="provenance_object_type_enum"),
        nullable=False, index=True,
    )
    object_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
    )

    # ── Source location ──────────────────────────────────────
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    document_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    page_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_pages.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_assets.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Bounding box (PDF points, top-left origin) ───────────
    bbox_x0: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_y0: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_x1: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_y1: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Character offsets within page raw_text ───────────────
    char_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_end: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Extraction metadata ──────────────────────────────────
    parser_name: Mapped[str] = mapped_column(String(128), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(64), nullable=False)
    extraction_timestamp: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_provenance_object", "object_type", "object_id"),
        Index("ix_provenance_document_page", "document_id", "page_id"),
    )


# ─────────────────────────────────────────────────────────
# Chunks
# ─────────────────────────────────────────────────────────


class Chunk(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Text/content chunk derived from a document page/section.
    Versioned via chunk_version for re-chunking support.
    """
    __tablename__ = "chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    page_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_pages.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_sections.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    chunk_type: Mapped[ChunkType] = mapped_column(
        SAEnum(ChunkType, name="chunk_type_enum"), nullable=False,
        default=ChunkType.TEXT, index=True,
    )
    chunk_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Position within document
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Bounding box (denormalized from Provenance for query performance)
    bbox_x0: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_y0: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_x1: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_y1: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Chemical flags
    contains_chemical_entities: Mapped[bool] = mapped_column(Boolean, default=False)
    chunker_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    chunker_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")  # type: ignore[name-defined]
    page: Mapped["DocumentPage | None"] = relationship("DocumentPage", back_populates="chunks")  # type: ignore[name-defined]
    section: Mapped["DocumentSection | None"] = relationship("DocumentSection", back_populates="chunks")  # type: ignore[name-defined]
    embeddings: Mapped[list["ChunkEmbedding"]] = relationship("ChunkEmbedding", back_populates="chunk")
    chemical_entities: Mapped[list["ChunkChemicalEntity"]] = relationship(
        "ChunkChemicalEntity", back_populates="chunk",
    )


class ChunkEmbedding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Model-independent vector embedding for a chunk.
    Multiple embedding types (text, chemical, multimodal) can coexist per chunk.
    Supports configurable dimensions and half-precision storage.
    """
    __tablename__ = "chunk_embeddings"
    __table_args__ = (
        UniqueConstraint("chunk_id", "model_name", "embedding_type", name="uq_chunk_embedding_model"),
        # HNSW index created via Alembic migration for each embedding type/dimension combo
    )

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    embedding_type: Mapped[EmbeddingModelType] = mapped_column(
        SAEnum(EmbeddingModelType, name="embedding_model_type_enum"),
        nullable=False, index=True,
    )
    model_name: Mapped[str] = mapped_column(String(256), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dimensions: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # Vector storage — dimension set per embedding type (see migrations)
    embedding: Mapped[list[float]] = mapped_column(Vector(3072), nullable=False)
    # Half-precision flag (for future storage optimization)
    is_half_precision: Mapped[bool] = mapped_column(Boolean, default=False)
    # Embedding quality
    norm: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    chunk: Mapped["Chunk"] = relationship("Chunk", back_populates="embeddings")
