"""
ChemRAG — Chemical Entity & Structure Models
=============================================
Covers: chemical_entities, chemical_structures, chunk_chemical_entities
"""
from __future__ import annotations

import uuid
import enum

from sqlalchemy import (
    Boolean, Enum as SAEnum, Float, ForeignKey,
    Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import TYPE_CHECKING

from backend.app.db.base import Base
from backend.app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.document import DocumentAsset
    from backend.app.models.chunk import Chunk


class EntityType(str, enum.Enum):
    COMPOUND = "compound"
    REACTION = "reaction"
    PROTEIN = "protein"
    GENE = "gene"
    DISEASE = "disease"
    ORGANISM = "organism"
    MATERIAL = "material"
    OTHER = "other"


class NormalizationSource(str, enum.Enum):
    PUBCHEM = "pubchem"
    CHEMBL = "chembl"
    CAS = "cas"
    MANUAL = "manual"
    UNKNOWN = "unknown"


class StructureSource(str, enum.Enum):
    DECIMER = "decimer"
    MOLSCRIBE = "molscribe"
    GROBID = "grobid"
    OSRA = "osra"
    MANUAL = "manual"


class ChemicalEntity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Normalized chemical entity — canonical representation after NER + normalization.
    Multiple document mentions map to the same ChemicalEntity via ChunkChemicalEntity.
    """
    __tablename__ = "chemical_entities"

    entity_type: Mapped[EntityType] = mapped_column(
        SAEnum(EntityType, name="entity_type_enum"), nullable=False, index=True,
    )
    # Normalized identifiers
    iupac_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    common_name: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    inchi: Mapped[str | None] = mapped_column(Text, nullable=True)
    inchi_key: Mapped[str | None] = mapped_column(String(27), nullable=True, unique=True, index=True)
    smiles: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_smiles: Mapped[str | None] = mapped_column(Text, nullable=True)
    # External DB identifiers
    pubchem_cid: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    chembl_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    cas_number: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    # Molecular properties
    molecular_formula: Mapped[str | None] = mapped_column(String(256), nullable=True)
    molecular_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    exact_mass: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Normalization metadata
    normalization_source: Mapped[NormalizationSource] = mapped_column(
        SAEnum(NormalizationSource, name="normalization_source_enum"),
        nullable=False, default=NormalizationSource.UNKNOWN,
    )
    normalization_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    synonyms: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    properties: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    structures: Mapped[list["ChemicalStructure"]] = relationship(
        "ChemicalStructure", back_populates="chemical_entity",
    )
    chunk_mentions: Mapped[list["ChunkChemicalEntity"]] = relationship(
        "ChunkChemicalEntity", back_populates="chemical_entity",
    )


class ChemicalStructure(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Raw extracted structure from a document asset (image of a chemical drawing).
    Linked to a ChemicalEntity after normalization.
    """
    __tablename__ = "chemical_structures"

    chemical_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chemical_entities.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    source_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_assets.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # Extracted representations
    smiles_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    mol_block: Mapped[str | None] = mapped_column(Text, nullable=True)
    inchi_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Extraction metadata
    extraction_source: Mapped[StructureSource] = mapped_column(
        SAEnum(StructureSource, name="structure_source_enum"), nullable=False,
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_valid_smiles: Mapped[bool] = mapped_column(Boolean, default=False)
    validation_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    chemical_entity: Mapped["ChemicalEntity | None"] = relationship(
        "ChemicalEntity", back_populates="structures",
    )
    source_asset: Mapped["DocumentAsset | None"] = relationship(  # type: ignore[name-defined]
        "DocumentAsset", back_populates="chemical_structures",
    )


class ChunkChemicalEntity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Many-to-many join between Chunk and ChemicalEntity.
    Stores mention text, span offsets, and NER confidence.
    """
    __tablename__ = "chunk_chemical_entities"
    __table_args__ = (
        Index("ix_cce_chunk_entity", "chunk_id", "chemical_entity_id"),
    )

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    chemical_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chemical_entities.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    mention_text: Mapped[str] = mapped_column(Text, nullable=False)
    mention_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mention_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ner_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ner_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    entity_label: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Relationships
    chunk: Mapped["Chunk"] = relationship("Chunk", back_populates="chemical_entities")  # type: ignore[name-defined]
    chemical_entity: Mapped["ChemicalEntity"] = relationship(
        "ChemicalEntity", back_populates="chunk_mentions",
    )
