"""
Regression Tests — Processing Pipeline Jobs Endpoint and PDF Streaming
======================================================================
Guarantees that:
1. GET /api/v1/documents/jobs returns HTTP 200 OK (not 422 Unprocessable Entity).
2. GET /api/v1/documents/jobs/{job_id} matches job detail endpoint correctly.
3. GET /api/v1/documents/{document_id}/file uses StreamingResponse without NameError.
"""
from __future__ import annotations

import uuid
import pytest
import httpx


@pytest.mark.asyncio
async def test_jobs_list_returns_200_not_422() -> None:
    """
    Verify that /documents/jobs is not intercepted by /{document_id}
    which previously caused a UUID parsing 422 error.
    """
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=10.0) as client:
        r = await client.get("/api/v1/documents/jobs")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_job_details_not_found() -> None:
    """Verify non-existent job ID returns 404 rather than 422."""
    fake_job_id = str(uuid.uuid4())
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=10.0) as client:
        r = await client.get(f"/api/v1/documents/jobs/{fake_job_id}")
        assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"


@pytest.mark.asyncio
async def test_document_file_not_found() -> None:
    """Verify non-existent document file returns 404 without 500 NameError."""
    fake_doc_id = str(uuid.uuid4())
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=10.0) as client:
        r = await client.get(f"/api/v1/documents/{fake_doc_id}/file")
        assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"


@pytest.mark.asyncio
async def test_documents_list_returns_200() -> None:
    """Verify list documents endpoint is functional."""
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=10.0) as client:
        r = await client.get("/api/v1/documents")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert isinstance(r.json(), list)
