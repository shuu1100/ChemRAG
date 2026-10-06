"""Initial schema — all ChemRAG tables, pgvector extension, and HNSW indexes

Revision ID: 0001
Revises: 
Create Date: 2026-10-06
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

# ── Vector dimension for default text embeddings ──────────────────────────────
# This is the default; additional embedding types may use different dimensions.
# Dimension is stored in chunk_embeddings.dimensions per row.
TEXT_EMBEDDING_DIM = 3072  # text-embedding-3-large


def upgrade() -> None:
    # ── 0. Enable extensions ──────────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    # ── 1. Enumerations ───────────────────────────────────────────────────────
    _create_enums()

    # ── 2. Organizations ──────────────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("max_documents", sa.Integer, default=1000, nullable=False),
        sa.Column("max_storage_bytes", sa.BigInteger, default=10 * 1024**3, nullable=False),
    )
    op.create_index("ix_organizations_id", "organizations", ["id"])
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)
    op.create_index("ix_organizations_deleted_at", "organizations", ["deleted_at"])

    # ── 3. Users ──────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("is_superuser", sa.Boolean, default=False, nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("email", "organization_id", name="uq_user_email_org"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_organization_id", "users", ["organization_id"])
    op.create_index("ix_users_email", "users", ["email"])

    # ── 4. Documents ──────────────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("doc_type", sa.Enum("pdf", "html", "xml", "docx", "txt", "other", name="document_type_enum"), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("authors", postgresql.JSONB, nullable=True),
        sa.Column("doi", sa.String(256), nullable=True),
        sa.Column("journal", sa.String(512), nullable=True),
        sa.Column("publication_year", sa.Integer, nullable=True),
        sa.Column("abstract", sa.Text, nullable=True),
        sa.Column("keywords", postgresql.JSONB, nullable=True),
        sa.Column("processing_state", sa.Enum("pending", "queued", "processing", "completed", "failed", "partial", name="processing_state_enum"), nullable=False, server_default="pending"),
        sa.Column("processing_error", sa.Text, nullable=True),
        sa.Column("is_public", sa.Boolean, default=False, nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_documents_id", "documents", ["id"])
    op.create_index("ix_documents_organization_id", "documents", ["organization_id"])
    op.create_index("ix_documents_sha256_hash", "documents", ["sha256_hash"])
    op.create_index("ix_documents_doi", "documents", ["doi"])
    op.create_index("ix_documents_processing_state", "documents", ["processing_state"])
    op.create_index("ix_documents_deleted_at", "documents", ["deleted_at"])

    # ── 5. Document Versions ──────────────────────────────────────────────────
    op.create_table(
        "document_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_current", sa.Boolean, default=True, nullable=False),
        sa.Column("parser_name", sa.String(128), nullable=False),
        sa.Column("parser_version", sa.String(64), nullable=False),
        sa.Column("parser_config", postgresql.JSONB, nullable=True),
        sa.Column("processing_state", sa.Enum("pending", "queued", "processing", "completed", "failed", "partial", name="processing_state_enum"), nullable=False, server_default="pending"),
        sa.Column("page_count", sa.Integer, nullable=True),
        sa.Column("word_count", sa.Integer, nullable=True),
        sa.Column("processing_error", sa.Text, nullable=True),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("document_id", "version_number", name="uq_doc_version"),
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])
    op.create_index("ix_document_versions_is_current", "document_versions", ["is_current"])

    # ── 6. Document Pages ─────────────────────────────────────────────────────
    op.create_table(
        "document_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_number", sa.Integer, nullable=False),
        sa.Column("width_pts", sa.Float, nullable=True),
        sa.Column("height_pts", sa.Float, nullable=True),
        sa.Column("raw_text", sa.Text, nullable=True),
        sa.Column("tei_xml", sa.Text, nullable=True),
        sa.Column("has_chemical_structures", sa.Boolean, default=False),
        sa.Column("has_tables", sa.Boolean, default=False),
        sa.Column("has_equations", sa.Boolean, default=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["document_versions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_document_pages_document_id", "document_pages", ["document_id"])
    op.create_index("ix_document_pages_version_id", "document_pages", ["version_id"])

    # ── 7. Document Assets ────────────────────────────────────────────────────
    op.create_table(
        "document_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_type", sa.Enum("image", "table", "equation", "chemical_structure", "figure", "supplementary", name="asset_type_enum"), nullable=False),
        sa.Column("bbox_x0", sa.Float, nullable=True),
        sa.Column("bbox_y0", sa.Float, nullable=True),
        sa.Column("bbox_x1", sa.Float, nullable=True),
        sa.Column("bbox_y1", sa.Float, nullable=True),
        sa.Column("storage_key", sa.String(1024), nullable=True),
        sa.Column("content_type", sa.String(128), nullable=True),
        sa.Column("caption", sa.Text, nullable=True),
        sa.Column("alt_text", sa.Text, nullable=True),
        sa.Column("extracted_text", sa.Text, nullable=True),
        sa.Column("processing_state", sa.Enum("pending", "queued", "processing", "completed", "failed", "partial", name="processing_state_enum"), nullable=False, server_default="pending"),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["page_id"], ["document_pages.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_document_assets_document_id", "document_assets", ["document_id"])
    op.create_index("ix_document_assets_page_id", "document_assets", ["page_id"])
    op.create_index("ix_document_assets_asset_type", "document_assets", ["asset_type"])

    # ── 8. Document Sections ──────────────────────────────────────────────────
    op.create_table(
        "document_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("section_type", sa.Enum("abstract", "introduction", "methods", "results", "discussion", "conclusion", "references", "supplementary", "other", name="section_type_enum"), nullable=False, server_default="other"),
        sa.Column("heading", sa.Text, nullable=True),
        sa.Column("section_order", sa.Integer, default=0, nullable=False),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("char_start", sa.Integer, nullable=True),
        sa.Column("char_end", sa.Integer, nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["page_id"], ["document_pages.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_document_sections_document_id", "document_sections", ["document_id"])

    # ── 9. Chemical Entities ──────────────────────────────────────────────────
    op.create_table(
        "chemical_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("entity_type", sa.Enum("compound", "reaction", "protein", "gene", "disease", "organism", "material", "other", name="entity_type_enum"), nullable=False),
        sa.Column("iupac_name", sa.Text, nullable=True),
        sa.Column("common_name", sa.Text, nullable=True),
        sa.Column("inchi", sa.Text, nullable=True),
        sa.Column("inchi_key", sa.String(27), nullable=True),
        sa.Column("smiles", sa.Text, nullable=True),
        sa.Column("canonical_smiles", sa.Text, nullable=True),
        sa.Column("pubchem_cid", sa.Integer, nullable=True),
        sa.Column("chembl_id", sa.String(32), nullable=True),
        sa.Column("cas_number", sa.String(32), nullable=True),
        sa.Column("molecular_formula", sa.String(256), nullable=True),
        sa.Column("molecular_weight", sa.Float, nullable=True),
        sa.Column("exact_mass", sa.Float, nullable=True),
        sa.Column("normalization_source", sa.Enum("pubchem", "chembl", "cas", "manual", "unknown", name="normalization_source_enum"), nullable=False, server_default="unknown"),
        sa.Column("normalization_confidence", sa.Float, nullable=True),
        sa.Column("synonyms", postgresql.JSONB, nullable=True),
        sa.Column("properties", postgresql.JSONB, nullable=True),
        sa.Column("is_verified", sa.Boolean, default=False),
    )
    op.create_index("ix_chemical_entities_id", "chemical_entities", ["id"])
    op.create_index("ix_chemical_entities_inchi_key", "chemical_entities", ["inchi_key"], unique=True)
    op.create_index("ix_chemical_entities_pubchem_cid", "chemical_entities", ["pubchem_cid"])
    op.create_index("ix_chemical_entities_chembl_id", "chemical_entities", ["chembl_id"])
    op.create_index("ix_chemical_entities_cas_number", "chemical_entities", ["cas_number"])
    op.create_index("ix_chemical_entities_entity_type", "chemical_entities", ["entity_type"])

    # ── 10. Chemical Structures ───────────────────────────────────────────────
    op.create_table(
        "chemical_structures",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("chemical_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("smiles_raw", sa.Text, nullable=True),
        sa.Column("mol_block", sa.Text, nullable=True),
        sa.Column("inchi_raw", sa.Text, nullable=True),
        sa.Column("extraction_source", sa.Enum("decimer", "molscribe", "grobid", "osra", "manual", name="structure_source_enum"), nullable=False),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("is_valid_smiles", sa.Boolean, default=False),
        sa.Column("validation_error", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["chemical_entity_id"], ["chemical_entities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_asset_id"], ["document_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_chemical_structures_chemical_entity_id", "chemical_structures", ["chemical_entity_id"])
    op.create_index("ix_chemical_structures_document_id", "chemical_structures", ["document_id"])

    # ── 11. Chunks ────────────────────────────────────────────────────────────
    op.create_table(
        "chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("chunk_type", sa.Enum("text", "table", "figure_caption", "equation", "chemical", "mixed", name="chunk_type_enum"), nullable=False, server_default="text"),
        sa.Column("chunk_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_current", sa.Boolean, default=True, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("token_count", sa.Integer, nullable=True),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("page_number", sa.Integer, nullable=True),
        sa.Column("bbox_x0", sa.Float, nullable=True),
        sa.Column("bbox_y0", sa.Float, nullable=True),
        sa.Column("bbox_x1", sa.Float, nullable=True),
        sa.Column("bbox_y1", sa.Float, nullable=True),
        sa.Column("contains_chemical_entities", sa.Boolean, default=False),
        sa.Column("chunker_name", sa.String(128), nullable=True),
        sa.Column("chunker_config", postgresql.JSONB, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["page_id"], ["document_pages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["section_id"], ["document_sections.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])
    op.create_index("ix_chunks_page_id", "chunks", ["page_id"])
    op.create_index("ix_chunks_section_id", "chunks", ["section_id"])
    op.create_index("ix_chunks_content_hash", "chunks", ["content_hash"])
    op.create_index("ix_chunks_is_current", "chunks", ["is_current"])
    op.create_index("ix_chunks_chunk_type", "chunks", ["chunk_type"])

    # ── 12. Chunk Embeddings (pgvector) ───────────────────────────────────────
    op.create_table(
        "chunk_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("embedding_type", sa.Enum("text", "chemical", "image", "multimodal", name="embedding_model_type_enum"), nullable=False),
        sa.Column("model_name", sa.String(256), nullable=False),
        sa.Column("model_version", sa.String(64), nullable=True),
        sa.Column("dimensions", sa.SmallInteger, nullable=False),
        sa.Column("embedding", Vector(TEXT_EMBEDDING_DIM), nullable=False),
        sa.Column("is_half_precision", sa.Boolean, default=False),
        sa.Column("norm", sa.Float, nullable=True),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("chunk_id", "model_name", "embedding_type", name="uq_chunk_embedding_model"),
    )
    op.create_index("ix_chunk_embeddings_chunk_id", "chunk_embeddings", ["chunk_id"])
    op.create_index("ix_chunk_embeddings_embedding_type", "chunk_embeddings", ["embedding_type"])

    # HNSW index for approximate nearest-neighbor search on text embeddings
    op.execute("""
        CREATE INDEX ix_chunk_embeddings_hnsw_text
        ON chunk_embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        WHERE embedding_type = 'text'
    """)

    # IVFFlat index for chemical embeddings (added when enough vectors exist)
    # Commented out here — add via a separate migration after data load:
    # CREATE INDEX CONCURRENTLY ix_chunk_embeddings_ivfflat_chemical
    # ON chunk_embeddings USING ivfflat (embedding vector_cosine_ops)
    # WITH (lists = 100) WHERE embedding_type = 'chemical'

    # ── 13. Chunk Chemical Entities ───────────────────────────────────────────
    op.create_table(
        "chunk_chemical_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chemical_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mention_text", sa.Text, nullable=False),
        sa.Column("mention_start", sa.Integer, nullable=True),
        sa.Column("mention_end", sa.Integer, nullable=True),
        sa.Column("ner_model", sa.String(128), nullable=True),
        sa.Column("ner_confidence", sa.Float, nullable=True),
        sa.Column("entity_label", sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chemical_entity_id"], ["chemical_entities.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_cce_chunk_entity", "chunk_chemical_entities", ["chunk_id", "chemical_entity_id"])

    # ── 14. Provenance ────────────────────────────────────────────────────────
    op.create_table(
        "provenance",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("object_type", sa.Enum("text", "table", "equation", "chemical_structure", "image", "chunk", "citation", name="provenance_object_type_enum"), nullable=False),
        sa.Column("object_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("page_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("page_number", sa.Integer, nullable=True),
        sa.Column("source_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("bbox_x0", sa.Float, nullable=True),
        sa.Column("bbox_y0", sa.Float, nullable=True),
        sa.Column("bbox_x1", sa.Float, nullable=True),
        sa.Column("bbox_y1", sa.Float, nullable=True),
        sa.Column("char_start", sa.Integer, nullable=True),
        sa.Column("char_end", sa.Integer, nullable=True),
        sa.Column("parser_name", sa.String(128), nullable=False),
        sa.Column("parser_version", sa.String(64), nullable=False),
        sa.Column("extraction_timestamp", sa.String(64), nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("extra", postgresql.JSONB, nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["page_id"], ["document_pages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_asset_id"], ["document_assets.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_provenance_object", "provenance", ["object_type", "object_id"])
    op.create_index("ix_provenance_document_page", "provenance", ["document_id", "page_id"])
    op.create_index("ix_provenance_object_type", "provenance", ["object_type"])

    # ── 15. Tables, TableRows, Experiments, Citations ─────────────────────────
    op.create_table(
        "tables",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("caption", sa.Text, nullable=True),
        sa.Column("html", sa.Text, nullable=True),
        sa.Column("headers", postgresql.JSONB, nullable=True),
        sa.Column("row_count", sa.Integer, nullable=True),
        sa.Column("col_count", sa.Integer, nullable=True),
        sa.Column("table_index", sa.Integer, default=0),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["page_id"], ["document_pages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["asset_id"], ["document_assets.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "table_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("table_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_index", sa.Integer, nullable=False),
        sa.Column("cells", postgresql.JSONB, nullable=True),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_table_rows_table_id", "table_rows", ["table_id"])

    op.create_table(
        "experiments",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("experimental_conditions", postgresql.JSONB, nullable=True),
        sa.Column("results", postgresql.JSONB, nullable=True),
        sa.Column("chemical_participants", postgresql.JSONB, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["section_id"], ["document_sections.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cited_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("citation_type", sa.Enum("article", "book", "patent", "preprint", "conference", "thesis", "other", name="citation_type_enum"), nullable=False, server_default="article"),
        sa.Column("citation_index", sa.Integer, nullable=True),
        sa.Column("raw_text", sa.Text, nullable=True),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("authors", postgresql.JSONB, nullable=True),
        sa.Column("doi", sa.String(256), nullable=True),
        sa.Column("year", sa.Integer, nullable=True),
        sa.Column("journal", sa.String(512), nullable=True),
        sa.Column("volume", sa.String(64), nullable=True),
        sa.Column("pages", sa.String(64), nullable=True),
        sa.Column("url", sa.String(1024), nullable=True),
        sa.Column("grobid_confidence", sa.Float, nullable=True),
        sa.ForeignKeyConstraint(["source_document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cited_document_id"], ["documents.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_citations_source_document_id", "citations", ["source_document_id"])
    op.create_index("ix_citations_doi", "citations", ["doi"])

    # ── 16. Ingestion Jobs ────────────────────────────────────────────────────
    op.create_table(
        "ingestion_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.Enum("pending", "queued", "processing", "completed", "failed", "partial", name="processing_state_enum"), nullable=False, server_default="pending"),
        sa.Column("current_phase", sa.String(64), nullable=True),
        sa.Column("progress_pct", sa.Float, default=0.0),
        sa.Column("celery_task_id", sa.String(128), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("error_traceback", sa.Text, nullable=True),
        sa.Column("phase_timings", postgresql.JSONB, nullable=True),
        sa.Column("config", postgresql.JSONB, nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ingestion_jobs_document_id", "ingestion_jobs", ["document_id"])
    op.create_index("ix_ingestion_jobs_organization_id", "ingestion_jobs", ["organization_id"])
    op.create_index("ix_ingestion_jobs_state", "ingestion_jobs", ["state"])
    op.create_index("ix_ingestion_jobs_celery_task_id", "ingestion_jobs", ["celery_task_id"])

    # ── 17. Agent Runs ────────────────────────────────────────────────────────
    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("state", sa.Enum("pending", "running", "completed", "failed", "cancelled", name="agent_run_state_enum"), nullable=False, server_default="pending"),
        sa.Column("user_query", sa.Text, nullable=False),
        sa.Column("query_filters", postgresql.JSONB, nullable=True),
        sa.Column("final_answer", sa.Text, nullable=True),
        sa.Column("answer_citations", postgresql.JSONB, nullable=True),
        sa.Column("graph_state", postgresql.JSONB, nullable=True),
        sa.Column("langgraph_thread_id", sa.String(128), nullable=True),
        sa.Column("total_tokens", sa.Integer, nullable=True),
        sa.Column("total_latency_ms", sa.Integer, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_agent_runs_organization_id", "agent_runs", ["organization_id"])
    op.create_index("ix_agent_runs_user_id", "agent_runs", ["user_id"])
    op.create_index("ix_agent_runs_state", "agent_runs", ["state"])
    op.create_index("ix_agent_runs_langgraph_thread_id", "agent_runs", ["langgraph_thread_id"])

    # ── 18. Tool Calls ────────────────────────────────────────────────────────
    op.create_table(
        "tool_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tool_name", sa.String(128), nullable=False),
        sa.Column("call_index", sa.Integer, default=0),
        sa.Column("input_args", postgresql.JSONB, nullable=True),
        sa.Column("output", postgresql.JSONB, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("tokens_used", sa.Integer, nullable=True),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_tool_calls_agent_run_id", "tool_calls", ["agent_run_id"])

    # ── 19. Retrieval Queries & Results ───────────────────────────────────────
    op.create_table(
        "retrieval_queries",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("query_text", sa.Text, nullable=False),
        sa.Column("query_embedding_model", sa.String(256), nullable=True),
        sa.Column("filters", postgresql.JSONB, nullable=True),
        sa.Column("strategy", sa.String(64), nullable=True),
        sa.Column("top_k", sa.Integer, default=10),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("result_count", sa.Integer, default=0),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_retrieval_queries_organization_id", "retrieval_queries", ["organization_id"])
    op.create_index("ix_retrieval_queries_agent_run_id", "retrieval_queries", ["agent_run_id"])

    op.create_table(
        "retrieval_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("query_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rank", sa.Integer, nullable=False),
        sa.Column("vector_score", sa.Float, nullable=True),
        sa.Column("bm25_score", sa.Float, nullable=True),
        sa.Column("rerank_score", sa.Float, nullable=True),
        sa.Column("final_score", sa.Float, nullable=False),
        sa.Column("was_used_in_answer", sa.Boolean, default=False),
        sa.Column("user_feedback", sa.Integer, nullable=True),
        sa.ForeignKeyConstraint(["query_id"], ["retrieval_queries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_retrieval_results_query_id", "retrieval_results", ["query_id"])
    op.create_index("ix_retrieval_results_chunk_id", "retrieval_results", ["chunk_id"])

    # ── 20. Safety Events ─────────────────────────────────────────────────────
    op.create_table(
        "safety_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decision", sa.Enum("allowed", "blocked", "flagged", "redacted", name="safety_decision_enum"), nullable=False),
        sa.Column("check_type", sa.String(128), nullable=False),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("input_text", sa.Text, nullable=True),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("flagged_content", postgresql.JSONB, nullable=True),
        sa.Column("reviewed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_safety_events_organization_id", "safety_events", ["organization_id"])
    op.create_index("ix_safety_events_decision", "safety_events", ["decision"])
    op.create_index("ix_safety_events_agent_run_id", "safety_events", ["agent_run_id"])

    # ── 21. Evaluation Runs & Cases ───────────────────────────────────────────
    op.create_table(
        "evaluation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("dataset_path", sa.String(1024), nullable=True),
        sa.Column("config", postgresql.JSONB, nullable=True),
        sa.Column("state", sa.Enum("pending", "queued", "processing", "completed", "failed", "partial", name="processing_state_enum"), nullable=False, server_default="pending"),
        sa.Column("metrics_summary", postgresql.JSONB, nullable=True),
        sa.Column("case_count", sa.Integer, default=0),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "evaluation_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("ground_truth", sa.Text, nullable=True),
        sa.Column("generated_answer", sa.Text, nullable=True),
        sa.Column("retrieved_contexts", postgresql.JSONB, nullable=True),
        sa.Column("faithfulness_score", sa.Float, nullable=True),
        sa.Column("answer_relevancy_score", sa.Float, nullable=True),
        sa.Column("context_precision_score", sa.Float, nullable=True),
        sa.Column("context_recall_score", sa.Float, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["evaluation_runs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_evaluation_cases_run_id", "evaluation_cases", ["run_id"])

    # ── 22. Audit Logs ────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.Enum("create", "read", "update", "delete", "login", "logout", "query", "upload", "export", name="audit_action_enum"), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("request_id", sa.String(128), nullable=True),
        sa.Column("extra", postgresql.JSONB, nullable=True),
        sa.Column("success", sa.Boolean, default=True),
        sa.Column("error_detail", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_audit_org_action", "audit_logs", ["organization_id", "action"])
    op.create_index("ix_audit_user_created", "audit_logs", ["user_id", "created_at"])


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("audit_logs")
    op.drop_table("evaluation_cases")
    op.drop_table("evaluation_runs")
    op.drop_table("safety_events")
    op.drop_table("retrieval_results")
    op.drop_table("retrieval_queries")
    op.drop_table("tool_calls")
    op.drop_table("agent_runs")
    op.drop_table("ingestion_jobs")
    op.drop_table("citations")
    op.drop_table("experiments")
    op.drop_table("table_rows")
    op.drop_table("tables")
    op.drop_table("provenance")
    op.drop_table("chunk_chemical_entities")
    op.drop_table("chunk_embeddings")
    op.drop_table("chunks")
    op.drop_table("chemical_structures")
    op.drop_table("chemical_entities")
    op.drop_table("document_sections")
    op.drop_table("document_assets")
    op.drop_table("document_pages")
    op.drop_table("document_versions")
    op.drop_table("documents")
    op.drop_table("users")
    op.drop_table("organizations")
    _drop_enums()


def _create_enums() -> None:
    """Create all ENUM types before table creation."""
    op.execute("CREATE TYPE document_type_enum AS ENUM ('pdf','html','xml','docx','txt','other')")
    op.execute("CREATE TYPE processing_state_enum AS ENUM ('pending','queued','processing','completed','failed','partial')")
    op.execute("CREATE TYPE asset_type_enum AS ENUM ('image','table','equation','chemical_structure','figure','supplementary')")
    op.execute("CREATE TYPE section_type_enum AS ENUM ('abstract','introduction','methods','results','discussion','conclusion','references','supplementary','other')")
    op.execute("CREATE TYPE chunk_type_enum AS ENUM ('text','table','figure_caption','equation','chemical','mixed')")
    op.execute("CREATE TYPE embedding_model_type_enum AS ENUM ('text','chemical','image','multimodal')")
    op.execute("CREATE TYPE provenance_object_type_enum AS ENUM ('text','table','equation','chemical_structure','image','chunk','citation')")
    op.execute("CREATE TYPE entity_type_enum AS ENUM ('compound','reaction','protein','gene','disease','organism','material','other')")
    op.execute("CREATE TYPE normalization_source_enum AS ENUM ('pubchem','chembl','cas','manual','unknown')")
    op.execute("CREATE TYPE structure_source_enum AS ENUM ('decimer','molscribe','grobid','osra','manual')")
    op.execute("CREATE TYPE citation_type_enum AS ENUM ('article','book','patent','preprint','conference','thesis','other')")
    op.execute("CREATE TYPE agent_run_state_enum AS ENUM ('pending','running','completed','failed','cancelled')")
    op.execute("CREATE TYPE safety_decision_enum AS ENUM ('allowed','blocked','flagged','redacted')")
    op.execute("CREATE TYPE audit_action_enum AS ENUM ('create','read','update','delete','login','logout','query','upload','export')")


def _drop_enums() -> None:
    """Drop all ENUM types after table removal."""
    for t in [
        "audit_action_enum", "safety_decision_enum", "agent_run_state_enum",
        "citation_type_enum", "structure_source_enum", "normalization_source_enum",
        "entity_type_enum", "provenance_object_type_enum", "embedding_model_type_enum",
        "chunk_type_enum", "section_type_enum", "asset_type_enum",
        "processing_state_enum", "document_type_enum",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {t}")
