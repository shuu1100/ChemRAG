"""
ChemRAG — Table & Experiment Models
=====================================
Covers: tables, table_rows, experiments, citations
"""
from __future__ import annotations

import uuid
import enum

from sqlalchemy import (
    Enum as SAEnum, Float, ForeignKey, Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CitationType(str, enum.Enum):
    ARTICLE = "article"
    BOOK = "book"
    PATENT = "patent"
    PREPRINT = "preprint"
    CONFERENCE = "conference"
    THESIS = "thesis"
    OTHER = "other"


class Table(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Extracted data table from a document page."""
    __tablename__ = "tables"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    page_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_pages.id", ondelete="SET NULL"),
        nullable=True,
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    html: Mapped[str | None] = mapped_column(Text, nullable=True)
    headers: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    col_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    table_index: Mapped[int] = mapped_column(Integer, default=0)

    rows: Mapped[list["TableRow"]] = relationship("TableRow", back_populates="table")


class TableRow(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Single row of a Table. Cells stored as JSONB."""
    __tablename__ = "table_rows"

    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tables.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    cells: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    table: Mapped["Table"] = relationship("Table", back_populates="rows")


class Experiment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Structured experimental record extracted from a document.
    Captures method, conditions, results, and chemical participants.
    """
    __tablename__ = "experiments"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_sections.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    experimental_conditions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    chemical_participants: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)


class Citation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Bibliographic citation extracted from a document.
    May link to another Document in the system (internal reference).
    """
    __tablename__ = "citations"

    source_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    cited_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    citation_type: Mapped[CitationType] = mapped_column(
        SAEnum(CitationType, name="citation_type_enum"), nullable=False,
        default=CitationType.ARTICLE,
    )
    citation_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    authors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    doi: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    journal: Mapped[str | None] = mapped_column(String(512), nullable=True)
    volume: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pages: Mapped[str | None] = mapped_column(String(64), nullable=True)
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    grobid_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
