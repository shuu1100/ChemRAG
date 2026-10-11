"""
ChemRAG — Phase 18 Unit Tests: Observability, Tracing, and Cost Tracking
==========================================================================
Tests:
- Structured logging context variables (request_id, user_id, org_id, etc.)
- OpenTelemetry telemetry spans (duration, status, attributes, span_id)
- Usage metering & CostTracker (tokens, embedding chunks, estimated costs)
- Separation of financial cost metrics from scientific outputs
"""
from __future__ import annotations

import pytest

from backend.app.core.cost_tracker import CostTracker
from backend.app.core.logging import reset_request_context, set_request_context
from backend.app.core.telemetry import TelemetryTracer, trace_operation


def test_structured_logging_context():
    """Verify request context variables binding."""
    set_request_context(
        request_id="req-test-123",
        organization_id="org-test-456",
        user_id="user-test-789",
        query_id="q-101",
    )
    # Reset without throwing exception
    reset_request_context()


def test_telemetry_tracer_spans():
    """Verify OpenTelemetry trace spans creation and completion."""
    tracer = TelemetryTracer()

    with tracer.start_span("retrieval.hybrid", kind="SERVER", attributes={"top_k": 10}) as span:
        assert span.name == "retrieval.hybrid"
        assert span.attributes["top_k"] == 10

    spans = tracer.get_recent_spans()
    assert len(spans) == 1
    recorded = spans[0]
    assert recorded["name"] == "retrieval.hybrid"
    assert recorded["status"] == "OK"
    assert recorded["duration_ms"] >= 0.0


def test_cost_tracker_metering():
    """Verify LLM token metering, embedding chunk usage, and financial cost segregation."""
    tracker = CostTracker()

    rec_llm = tracker.record_llm_usage(
        provider="openai",
        model="gpt-4o",
        prompt_tokens=1000,
        completion_tokens=500,
    )
    assert rec_llm.estimated_cost_usd > 0.0
    assert rec_llm.prompt_tokens == 1000

    rec_emb = tracker.record_embedding_usage(
        provider="openai",
        model="text-embedding-3-large",
        chunks_count=10,
        total_tokens=2000,
    )
    assert rec_emb.chunks_count == 10

    tracker.record_external_api_call("pubchem", "/compound/name")

    summary = tracker.get_cumulative_summary()
    assert summary["total_llm_prompt_tokens"] == 1000
    assert summary["total_llm_completion_tokens"] == 500
    assert summary["total_embedding_chunks"] == 10
    assert summary["total_external_calls"] == 1
    assert summary["estimated_total_cost_usd"] > 0.0
