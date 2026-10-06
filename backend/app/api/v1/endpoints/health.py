"""
ChemRAG — Health & Readiness Endpoints
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter, status
from pydantic import BaseModel

from backend.app.core.config import get_settings

router = APIRouter()
_START_TIME = time.time()


class ServiceStatus(BaseModel):
    name: str
    status: str  # "ok" | "degraded" | "unavailable"
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    env: str
    version: str
    uptime_seconds: float
    timestamp: datetime
    services: list[ServiceStatus]


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description=(
        "Returns the operational status of the ChemRAG API and its dependent services. "
        "Used by Docker, load balancers, and Kubernetes probes."
    ),
)
async def health_check() -> HealthResponse:
    """
    Shallow health check — always returns 200 if the process is alive.
    Deep connectivity checks are done in /readiness.
    """
    settings = get_settings()
    return HealthResponse(
        status="ok",
        env=settings.app_env.value,
        version="0.1.0",
        uptime_seconds=round(time.time() - _START_TIME, 2),
        timestamp=datetime.now(timezone.utc),
        services=[
            ServiceStatus(name="api", status="ok"),
            # Phase 02 will add: database, redis
            # Phase 08 will add: vector_store, embedding_model
            # Phase 03 will add: grobid
        ],
    )


@router.get(
    "/readiness",
    response_model=HealthResponse,
    summary="Readiness probe",
    description="Deep connectivity check — fails if any critical service is unavailable.",
)
async def readiness_check() -> HealthResponse:
    """
    Readiness probe.  Actual DB/Redis pings will be added in Phase 02.
    """
    return await health_check()


@router.get("/liveness", status_code=status.HTTP_200_OK, summary="Liveness probe")
async def liveness() -> dict[str, str]:
    """Minimal liveness probe for Kubernetes / Docker HEALTHCHECK."""
    return {"status": "alive"}
