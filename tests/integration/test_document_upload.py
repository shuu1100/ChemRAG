"""
ChemRAG — Document Upload & Management Integration Tests
=========================================================
Tests:
- PDF MIME type and extension validation
- File size and empty file limits
- Magic byte validation (%PDF-)
- SHA-256 calculation and duplicate detection (409 Conflict)
- Asynchronous job dispatch (returns pending status without synchronous parse)
- Document metadata retrieval
- Ingestion job status and retry/resume endpoint
"""
from __future__ import annotations

from datetime import datetime, timezone
import io
import uuid
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.app.db.session import get_db_session
from backend.app.main import app
from backend.app.models.document import Document, DocumentGenre, DocumentType, DocumentVersion, ProcessingState
from backend.app.models.pipeline import IngestionJob
from backend.app.services.ingestion.stages import IngestionStage


@pytest.fixture
def mock_db():
    """In-memory mock database store for testing endpoints."""
    docs: dict[uuid.UUID, Document] = {}
    versions: dict[uuid.UUID, DocumentVersion] = {}
    jobs: dict[uuid.UUID, IngestionJob] = {}

    class MockSession:
        def add(self, obj):
            if isinstance(obj, Document):
                if not obj.id:
                    obj.id = uuid.uuid4()
                docs[obj.id] = obj
            elif isinstance(obj, DocumentVersion):
                if not obj.id:
                    obj.id = uuid.uuid4()
                versions[obj.id] = obj
            elif isinstance(obj, IngestionJob):
                if not obj.id:
                    obj.id = uuid.uuid4()
                jobs[obj.id] = obj

        async def flush(self):
            pass

        async def commit(self):
            pass

        async def refresh(self, obj):
            pass

        async def execute(self, statement):
            result = MagicMock()
            query_str = str(statement)
            where_clause = query_str.split("WHERE")[-1] if "WHERE" in query_str else ""
            if "documents.sha256_hash" in where_clause:
                result.scalar_one_or_none.return_value = getattr(self, "_dup_doc", None)
            elif "documents.id" in where_clause:
                doc_id = getattr(self, "_requested_doc_id", None)
                result.scalar_one_or_none.return_value = docs.get(doc_id)
            elif "ingestion_jobs.id" in where_clause:
                job_id = getattr(self, "_requested_job_id", None)
                result.scalar_one_or_none.return_value = jobs.get(job_id)
            elif "FROM document_versions" in query_str:
                result.scalar_one_or_none.return_value = list(versions.values())[-1] if versions else None
            else:
                result.scalar_one_or_none.return_value = None
            return result



    mock_sess = MockSession()

    async def override_get_db():
        yield mock_sess

    app.dependency_overrides[get_db_session] = override_get_db
    yield mock_sess
    app.dependency_overrides.clear()


@pytest.fixture
def client(mock_db) -> TestClient:
    return TestClient(app)


class TestDocumentUploadAPI:
    def test_upload_rejects_non_pdf_extension(self, client: TestClient) -> None:
        file_content = b"%PDF-1.4 test content"
        files = {"file": ("data.txt", io.BytesIO(file_content), "text/plain")}
        data = {"organization_id": str(uuid.uuid4())}

        response = client.post("/api/v1/documents/upload", files=files, data=data)
        assert response.status_code == 400
        assert "Only .pdf files are accepted" in response.json()["detail"]

    def test_upload_rejects_empty_file(self, client: TestClient) -> None:
        files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
        data = {"organization_id": str(uuid.uuid4())}

        response = client.post("/api/v1/documents/upload", files=files, data=data)
        assert response.status_code == 400
        assert "empty" in response.json()["detail"]

    def test_upload_rejects_corrupted_header(self, client: TestClient) -> None:
        files = {"file": ("corrupted.pdf", io.BytesIO(b"NOT A REAL PDF FILE CONTENT"), "application/pdf")}
        data = {"organization_id": str(uuid.uuid4())}

        response = client.post("/api/v1/documents/upload", files=files, data=data)
        assert response.status_code == 400
        assert "%PDF-" in response.json()["detail"]

    def test_upload_valid_pdf_creates_pending_job(self, client: TestClient, mock_db) -> None:
        valid_pdf = b"%PDF-1.4\n%Chemical Research Paper\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        files = {"file": ("synthesis_paper.pdf", io.BytesIO(valid_pdf), "application/pdf")}
        org_id = uuid.uuid4()
        data = {"organization_id": str(org_id), "is_public": "true"}

        response = client.post("/api/v1/documents/upload", files=files, data=data)

        assert response.status_code == 202
        body = response.json()
        assert "document_id" in body
        assert "version_id" in body
        assert "job_id" in body
        assert body["status"] == "pending"
        assert body["is_duplicate"] is False
        assert body["filename"] == "synthesis_paper.pdf"
        assert len(body["sha256_hash"]) == 64

    def test_duplicate_file_returns_409_conflict(self, client: TestClient, mock_db) -> None:
        existing_doc_id = uuid.uuid4()
        existing_org_id = uuid.uuid4()
        existing_doc = Document(
            id=existing_doc_id,
            organization_id=existing_org_id,
            filename="existing_dup.pdf",
            file_size_bytes=100,
            content_type="application/pdf",
            doc_type=DocumentType.PDF,
            storage_key="test/key",
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            processing_state=ProcessingState.COMPLETED,
        )
        mock_db._dup_doc = existing_doc

        valid_pdf = b"%PDF-1.4 duplicate sample"
        files = {"file": ("existing_dup.pdf", io.BytesIO(valid_pdf), "application/pdf")}
        data = {"organization_id": str(existing_org_id)}

        response = client.post("/api/v1/documents/upload", files=files, data=data)
        assert response.status_code == 409
        body = response.json()
        assert body["is_duplicate"] is True
        assert body["document_id"] == str(existing_doc_id)
        assert "Duplicate document detected" in body["message"]

    def test_get_document_by_id(self, client: TestClient, mock_db) -> None:
        doc_id = uuid.uuid4()
        doc = Document(
            id=doc_id,
            organization_id=uuid.uuid4(),
            filename="retrieved_paper.pdf",
            file_size_bytes=5000,
            content_type="application/pdf",
            doc_type=DocumentType.PDF,
            genre=DocumentGenre.RESEARCH_PAPER,
            genre_confidence=0.88,
            storage_key="test/retrieved.pdf",
            sha256_hash="somehashvalue",
            processing_state=ProcessingState.COMPLETED,
            is_public=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_db.add(doc)
        mock_db._requested_doc_id = doc_id

        response = client.get(f"/api/v1/documents/{doc_id}")
        assert response.status_code == 200


        data = response.json()
        assert data["id"] == str(doc_id)
        assert data["filename"] == "retrieved_paper.pdf"
        assert data["genre"] == "research_paper"
        assert data["genre_confidence"] == 0.88

    def test_get_document_not_found(self, client: TestClient, mock_db) -> None:
        mock_db._requested_doc_id = uuid.uuid4()
        response = client.get(f"/api/v1/documents/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_get_job_by_id(self, client: TestClient, mock_db) -> None:
        job_id = uuid.uuid4()
        job = IngestionJob(
            id=job_id,
            document_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            state=ProcessingState.PROCESSING,
            current_phase="CLASSIFY",
            progress_pct=30.0,
            config={"stages_completed": ["UPLOAD", "VALIDATE", "STORE"]},
        )
        mock_db.add(job)
        mock_db._requested_job_id = job_id

        response = client.get(f"/api/v1/documents/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(job_id)
        assert data["state"] == "processing"
        assert data["current_phase"] == "CLASSIFY"
        assert data["progress_pct"] == 30.0
        assert data["stages_completed"] == ["UPLOAD", "VALIDATE", "STORE"]

    def test_retry_job_resumes(self, client: TestClient, mock_db) -> None:
        job_id = uuid.uuid4()
        job = IngestionJob(
            id=job_id,
            document_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            state=ProcessingState.FAILED,
            current_phase="EXTRACT",
            progress_pct=50.0,
            error_message="Connection timed out",
            config={"stages_completed": ["UPLOAD", "VALIDATE", "STORE", "CLASSIFY", "PARSE"]},
        )
        mock_db.add(job)
        mock_db._requested_job_id = job_id

        response = client.post(f"/api/v1/documents/jobs/{job_id}/retry")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(job_id)
        assert data["state"] == "queued"
        assert data["error_message"] is None
