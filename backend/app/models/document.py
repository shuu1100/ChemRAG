"""
ChemRAG — Document & Document-Asset Models
===========================================
Covers: documents, document_versions, document_pages, document_assets,
        document_sections
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum as SAEnum, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

import enum


# ─────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────


class ProcessingState(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class DocumentType(str, enum.Enum):
    PDF = "pdf"
    HTML = "html"
    XML = "xml"
    DOCX = "docx"
    TXT = "txt"
    OTHER = "other"


class DocumentGenre(str, enum.Enum):
    RESEARCH_PAPER = "research_paper"
    TEXTBOOK = "textbook"
    EXPERIMENTAL_REPORT = "experimental_report"
    SOP = "sop"
    SDS = "sds"
    TECHNICAL_REPORT = "technical_report"
    UNKNOWN = "unknown"



class AssetType(str, enum.Enum):
    IMAGE = "image"
    TABLE = "table"
    EQUATION = "equation"
    CHEMICAL_STRUCTURE = "chemical_structure"
    FIGURE = "figure"
    SUPPLEMENTARY = "supplementary"


class SectionType(str, enum.Enum):
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    METHODS = "methods"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    REFERENCES = "references"
    SUPPLEMENTARY = "supplementary"
    OTHER = "other"


# ─────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Root document record. Immutable metadata about the original file.
    Actual versioned content lives in DocumentVersion.
    """
    __tablename__ = "documents"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    # Original file info
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    doc_type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType, name="document_type_enum"), nullable=False,
        default=DocumentType.PDF,
    )
    genre: Mapped[DocumentGenre] = mapped_column(
        SAEnum(DocumentGenre, name="document_genre_enum"), nullable=False,
        default=DocumentGenre.UNKNOWN, index=True,
    )
    genre_confidence: Mapped[float] = mapped_column(Float, default=0.0)

    # Storage reference
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Bibliographic metadata (enriched from GROBID)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    authors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    doi: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    journal: Mapped[str | None] = mapped_column(String(512), nullable=True)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # State
    processing_state: Mapped[ProcessingState] = mapped_column(
        SAEnum(ProcessingState, name="processing_state_enum"), nullable=False,
        default=ProcessingState.PENDING, index=True,
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="documents")  # type: ignore[name-defined]
    uploaded_by: Mapped["User | None"] = relationship("User", back_populates="documents")  # type: ignore[name-defined]
    versions: Mapped[list["DocumentVersion"]] = relationship("DocumentVersion", back_populates="document")
    pages: Mapped[list["DocumentPage"]] = relationship("DocumentPage", back_populates="document")
    sections: Mapped[list["DocumentSection"]] = relationship("DocumentSection", back_populates="document")
    assets: Mapped[list["DocumentAsset"]] = relationship("DocumentAsset", back_populates="document")
    chunks: Mapped[list["Chunk"]] = relationship("Chunk", back_populates="document")
    ingestion_jobs: Mapped[list["IngestionJob"]] = relationship("IngestionJob", back_populates="document")


class DocumentVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Versioned snapshot of a document's parsed content.
    Supports re-processing with different parser configs.
    """
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_doc_version"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    parser_name: Mapped[str] = mapped_column(String(128), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    processing_state: Mapped[ProcessingState] = mapped_column(
        SAEnum(ProcessingState, name="processing_state_enum"), nullable=False,
        default=ProcessingState.PENDING,
    )
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="versions")
    pages: Mapped[list["DocumentPage"]] = relationship("DocumentPage", back_populates="version")


class DocumentPage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Single page of a parsed document. The provenance anchor for all extracted objects.
    """
    __tablename__ = "document_pages"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)           # 1-indexed
    width_pts: Mapped[float | None] = mapped_column(Float, nullable=True)       # PDF point dimensions
    height_pts: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    tei_xml: Mapped[str | None] = mapped_column(Text, nullable=True)            # GROBID TEI output
    has_chemical_structures: Mapped[bool] = mapped_column(Boolean, default=False)
    has_tables: Mapped[bool] = mapped_column(Boolean, default=False)
    has_equations: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="pages")
    version: Mapped["DocumentVersion"] = relationship("DocumentVersion", back_populates="pages")
    assets: Mapped[list["DocumentAsset"]] = relationship("DocumentAsset", back_populates="page")
    sections: Mapped[list["DocumentSection"]] = relationship("DocumentSection", back_populates="page")
    chunks: Mapped[list["Chunk"]] = relationship("Chunk", back_populates="page")


class DocumentAsset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Extracted visual asset from a page (image, table, equation, chemical structure).
    Stores bounding box for provenance.
    """
    __tablename__ = "document_assets"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_pages.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    asset_type: Mapped[AssetType] = mapped_column(
        SAEnum(AssetType, name="asset_type_enum"), nullable=False, index=True,
    )
    # Bounding box (in PDF points, origin top-left)
    bbox_x0: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_y0: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_x1: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_y1: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Storage
    storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Extracted content
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    alt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_state: Mapped[ProcessingState] = mapped_column(
        SAEnum(ProcessingState, name="processing_state_enum"), nullable=False,
        default=ProcessingState.PENDING,
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="assets")
    page: Mapped["DocumentPage"] = relationship("DocumentPage", back_populates="assets")
    chemical_structures: Mapped[list["ChemicalStructure"]] = relationship(
        "ChemicalStructure", back_populates="source_asset",
    )


class DocumentSection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Logical section of a document (Abstract, Methods, Results, etc.).
    Extracted by GROBID and used for contextual chunking.
    """
    __tablename__ = "document_sections"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    page_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_pages.id", ondelete="SET NULL"),
        nullable=True,
    )
    section_type: Mapped[SectionType] = mapped_column(
        SAEnum(SectionType, name="section_type_enum"), nullable=False,
        default=SectionType.OTHER,
    )
    heading: Mapped[str | None] = mapped_column(Text, nullable=True)
    section_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Character offsets within the page raw_text
    char_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_end: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="sections")
    page: Mapped["DocumentPage | None"] = relationship("DocumentPage", back_populates="sections")
    chunks: Mapped[list["Chunk"]] = relationship("Chunk", back_populates="section")
