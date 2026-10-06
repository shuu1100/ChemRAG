"""
Phase 01 — Health Endpoint Integration Tests
=============================================
Tests the /api/v1/health endpoint using FastAPI TestClient.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


class TestHealthEndpoints:
    def test_health_returns_200(self, client: TestClient) -> None:
        r = client.get("/api/v1/health")
        assert r.status_code == 200

    def test_health_response_schema(self, client: TestClient) -> None:
        r = client.get("/api/v1/health")
        body = r.json()
        assert body["status"] == "ok"
        assert "env" in body
        assert "version" in body
        assert "uptime_seconds" in body
        assert isinstance(body["services"], list)

    def test_liveness_returns_200(self, client: TestClient) -> None:
        r = client.get("/api/v1/health/liveness")
        assert r.status_code == 200
        assert r.json()["status"] == "alive"

    def test_readiness_returns_200(self, client: TestClient) -> None:
        r = client.get("/api/v1/health/readiness")
        assert r.status_code == 200
