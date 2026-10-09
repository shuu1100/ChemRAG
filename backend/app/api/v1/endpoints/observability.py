"""
ChemRAG — Observability REST API Endpoints
==========================================
Endpoints:
- GET /observability/usage   (Cumulative token metering & estimated costs)
- GET /observability/traces  (Recent trace span telemetry)
"""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, status

from backend.app.core.cost_tracker import cost_tracker
from backend.app.core.telemetry import tracer

router = APIRouter()


@router.get(
    "/usage",
    status_code=status.HTTP_200_OK,
    summary="Get cumulative LLM token metering and usage costs",
)
async def get_usage_metrics() -> Dict[str, Any]:
    """Fetch usage breakdown, token totals, and estimated financial costs."""
    return cost_tracker.get_cumulative_summary()


@router.get(
    "/traces",
    status_code=status.HTTP_200_OK,
    summary="Get recent OpenTelemetry-ready trace spans",
)
async def get_trace_spans(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch recent execution trace spans across system boundaries."""
    return tracer.get_recent_spans(limit=limit)
