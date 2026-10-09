"""
ChemRAG — Integration Tests for Chat & Agent Trace Endpoints
============================================================
Tests:
- POST /api/v1/chat endpoint (query execution, response formatting, citations, operational trace)
- GET  /api/v1/chat/trace/{run_id} endpoint (trace retrieval for specific run ID)
- GET  /api/v1/chat/history/{conversation_id} endpoint (conversation history retrieval)
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_chat_endpoint_empty_query(client):
    """Verify empty query returns 400 Bad Request."""
    response = client.post("/api/v1/chat", json={"query": "   "})
    assert response.status_code == 400
    assert "Query text cannot be empty" in response.json()["detail"]


def test_chat_endpoint_execution(client):
    """Verify POST /api/v1/chat executes multi-agent graph and returns formatted response."""
    payload = {
        "query": "What is the boiling point of Ethanol?",
        "conversation_id": "conv-test-101",
    }

    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["conversation_id"] == "conv-test-101"
    assert data["query"] == "What is the boiling point of Ethanol?"
    assert "run_id" in data
    assert "answer" in data
    assert "agent_trace" in data
    assert isinstance(data["agent_trace"], list)
    assert len(data["agent_trace"]) > 0

    # Test trace retrieval endpoint
    run_id = data["run_id"]
    trace_res = client.get(f"/api/v1/chat/trace/{run_id}")
    assert trace_res.status_code == 200
    trace_data = trace_res.json()
    assert trace_data["run_id"] == run_id
    assert "agent_trace" in trace_data


def test_chat_history_endpoint(client):
    """Verify GET /api/v1/chat/history/{conversation_id} retrieves past conversation runs."""
    conv_id = "conv-hist-202"
    client.post("/api/v1/chat", json={"query": "Question 1", "conversation_id": conv_id})
    client.post("/api/v1/chat", json={"query": "Question 2", "conversation_id": conv_id})

    history_res = client.get(f"/api/v1/chat/history/{conv_id}")
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) >= 2
    assert history[0]["query"] == "Question 1"
    assert history[1]["query"] == "Question 2"
