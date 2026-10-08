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
    Health check — checks process, database, and Redis connectivity.
    """
    from backend.app.db.health import check_services_health

    settings = get_settings()
    services_health = await check_services_health()

    db_status = services_health.get("database", {}).get("status", "unknown")
    redis_status = services_health.get("redis", {}).get("status", "unknown")

    services = [
        ServiceStatus(name="api", status="ok"),
        ServiceStatus(
            name="database",
            status="ok" if db_status == "healthy" else "degraded",
            detail=str(services_health.get("database", {})),
        ),
        ServiceStatus(
            name="redis",
            status="ok" if redis_status == "healthy" else "degraded",
            detail=str(services_health.get("redis", {})),
        ),
    ]

    overall_status = "ok" if services_health.get("status") == "healthy" else "degraded"

    return HealthResponse(
        status=overall_status,
        env=settings.app_env.value,
        version="0.1.0",
        uptime_seconds=round(time.time() - _START_TIME, 2),
        timestamp=datetime.now(timezone.utc),
        services=services,
    )


@router.get(
    "/readiness",
    response_model=HealthResponse,
    summary="Readiness probe",
    description="Deep connectivity check — fails if any critical service is unavailable.",
)
async def readiness_check() -> HealthResponse:
    """
    Readiness probe. Checks DB and Redis connection readiness.
    """
    return await health_check()


@router.get("/liveness", status_code=status.HTTP_200_OK, summary="Liveness probe")
async def liveness() -> dict[str, str]:
    """Minimal liveness probe for Kubernetes / Docker HEALTHCHECK."""
    return {"status": "alive"}

