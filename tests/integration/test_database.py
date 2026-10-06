"""
ChemRAG — Database Health & Connectivity Tests
===============================================
Tests that can run against a live PostgreSQL instance.
Requires: POSTGRES_* env vars pointing to a running database.
Mark these with @pytest.mark.integration to skip in unit-test runs.
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio

pytestmark = pytest.mark.integration


@pytest.mark.integration
class TestDatabaseConnectivity:
    """
    These tests require a running PostgreSQL instance.
    Run with: pytest tests/integration/test_database.py -m integration -v
    """

    def test_database_url_builds(self) -> None:
        """The DB URL helper produces a valid asyncpg URL without secrets leaking."""
        from backend.app.core.config import DatabaseConfig
        db = DatabaseConfig()
        url = db.async_url
        assert url.startswith("postgresql+asyncpg://")
        assert db.password.get_secret_value() not in repr(db)

    def test_sync_url_builds(self) -> None:
        from backend.app.core.config import DatabaseConfig
        db = DatabaseConfig()
        url = db.sync_url
        assert url.startswith("postgresql+psycopg2://")

    def test_engine_creates(self) -> None:
        """Engine factory should not raise without a live connection."""
        from backend.app.db.session import get_engine
        engine = get_engine()
        assert engine is not None


@pytest.mark.integration
class TestProvenanceModel:
    """
    Verify that the Provenance model can trace chunk → page → bounding box.
    These tests use in-memory/mock data to validate the model fields
    without needing a live DB.
    """

    def test_provenance_has_required_fields(self) -> None:
        from backend.app.models.chunk import Provenance, ProvenanceObjectType
        # Validate column attributes exist on the mapper
        mapper_attrs = [c.key for c in Provenance.__mapper__.columns]
        required = [
            "id", "object_type", "object_id",
            "document_id", "document_version_id", "page_id", "page_number",
            "source_asset_id",
            "bbox_x0", "bbox_y0", "bbox_x1", "bbox_y1",
            "char_start", "char_end",
            "parser_name", "parser_version",
            "extraction_timestamp", "confidence",
        ]
        for field in required:
            assert field in mapper_attrs, f"Provenance missing field: {field}"

    def test_chunk_has_bbox_fields(self) -> None:
        from backend.app.models.chunk import Chunk
        attrs = [c.key for c in Chunk.__mapper__.columns]
        for field in ["bbox_x0", "bbox_y0", "bbox_x1", "bbox_y1", "page_number", "page_id"]:
            assert field in attrs, f"Chunk missing field: {field}"

    def test_chunk_embedding_has_vector_column(self) -> None:
        from backend.app.models.chunk import ChunkEmbedding
        attrs = [c.key for c in ChunkEmbedding.__mapper__.columns]
        assert "embedding" in attrs
        assert "dimensions" in attrs
        assert "model_name" in attrs
        assert "embedding_type" in attrs


@pytest.mark.integration
class TestModelRelationships:
    """Validate that all relationships are properly configured."""

    def test_document_has_pages_relationship(self) -> None:
        from backend.app.models.document import Document
        assert hasattr(Document, "pages")
        assert hasattr(Document, "versions")
        assert hasattr(Document, "chunks")
        assert hasattr(Document, "assets")

    def test_chunk_has_embeddings_relationship(self) -> None:
        from backend.app.models.chunk import Chunk
        assert hasattr(Chunk, "embeddings")
        assert hasattr(Chunk, "chemical_entities")

    def test_chemical_entity_has_structures(self) -> None:
        from backend.app.models.chemical import ChemicalEntity
        assert hasattr(ChemicalEntity, "structures")
        assert hasattr(ChemicalEntity, "chunk_mentions")

    def test_agent_run_has_tool_calls(self) -> None:
        from backend.app.models.pipeline import AgentRun
        assert hasattr(AgentRun, "tool_calls")
        assert hasattr(AgentRun, "safety_events")

    def test_organization_has_users_and_documents(self) -> None:
        from backend.app.models.user import Organization
        assert hasattr(Organization, "users")
        assert hasattr(Organization, "documents")


@pytest.mark.integration
class TestAllModelsImport:
    """All models must be importable without errors."""

    def test_models_package_imports(self) -> None:
        import backend.app.models as m
        assert m.Base is not None
        assert m.Document is not None
        assert m.Chunk is not None
        assert m.ChunkEmbedding is not None
        assert m.Provenance is not None
        assert m.ChemicalEntity is not None
        assert m.AgentRun is not None
        assert m.AuditLog is not None

    def test_all_tables_registered(self) -> None:
        import backend.app.models  # noqa
        from backend.app.db.base import Base
        expected_tables = {
            "organizations", "users", "documents", "document_versions",
            "document_pages", "document_assets", "document_sections",
            "chunks", "chunk_embeddings", "provenance",
            "chemical_entities", "chemical_structures", "chunk_chemical_entities",
            "tables", "table_rows", "experiments", "citations",
            "ingestion_jobs", "agent_runs", "tool_calls",
            "retrieval_queries", "retrieval_results",
            "safety_events", "evaluation_runs", "evaluation_cases",
            "audit_logs",
        }
        registered = set(Base.metadata.tables.keys())
        missing = expected_tables - registered
        assert not missing, f"Tables not registered in metadata: {missing}"
