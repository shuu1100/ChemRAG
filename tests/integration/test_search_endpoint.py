"""
Search Endpoint Integration Tests.
Tests the /api/v1/search endpoint using FastAPI TestClient.
"""

from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient

from unittest.mock import AsyncMock, MagicMock
from backend.app.db.session import get_db_session
from backend.app.main import app


@pytest.fixture(autouse=True)
def override_db():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def _get_test_db():
        yield mock_session

    app.dependency_overrides[get_db_session] = _get_test_db
    yield
    app.dependency_overrides.pop(get_db_session, None)


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


class TestSearchEndpoint:
    def test_search_endpoint_returns_200(self, client: TestClient) -> None:
        payload = {
            "query_text": "acetylsalicylic acid aspirin synthesis",
            "top_k": 5,
            "rerank": True,
            "build_context": True,
        }
        resp = client.post("/api/v1/search", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["query_text"] == "acetylsalicylic acid aspirin synthesis"
        assert "results" in data
        assert "latency_ms" in data
        assert data["latency_ms"] >= 0.0

    def test_search_rejects_empty_query(self, client: TestClient) -> None:
        payload = {
            "query_text": "",
            "top_k": 5,
        }
        resp = client.post("/api/v1/search", json=payload)
        assert resp.status_code == 422  # Pydantic validation error

    def test_search_with_chemical_query_and_filters(self, client: TestClient) -> None:
        org_id = str(uuid.uuid4())
        payload = {
            "query_text": "benzene reduction",
            "query_smiles": "c1ccccc1",
            "top_k": 3,
            "filters": {
                "organization_id": org_id,
            },
            "rerank": False,
            "build_context": False,
        }
        resp = client.post("/api/v1/search", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["query_smiles"] == "c1ccccc1"
        assert isinstance(data["results"], list)
