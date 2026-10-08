"""
ChemRAG — Database & Cache Health Check Service
===============================================
Provides async health check utilities for PostgreSQL (+pgvector) and Redis.
Used by API health endpoints and CLI status tools.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict

from sqlalchemy import text

from backend.app.db.session import get_session_factory
from backend.app.db.redis import get_redis_client

logger = logging.getLogger(__name__)


async def check_database_health() -> Dict[str, Any]:
    """
    Executes a PING / SELECT 1 query on PostgreSQL and verifies pgvector extension status.
    Returns status dict with response time and extension info.
    """
    start_time = time.perf_counter()
    session_factory = get_session_factory()
    try:
        async with session_factory() as session:
            # Check basic connection
            result = await session.execute(text("SELECT 1"))
            val = result.scalar()
            if val != 1:
                return {
                    "status": "unhealthy",
                    "error": "Unexpected query response",
                    "latency_ms": round((time.perf_counter() - start_time) * 1000, 2),
                }
            
            # Check pgvector extension presence
            ext_result = await session.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            )
            has_pgvector = ext_result.scalar() is not None
            
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "status": "healthy",
                "database": "postgresql",
                "pgvector_enabled": has_pgvector,
                "latency_ms": latency_ms,
            }
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "postgresql",
            "error": str(e),
            "latency_ms": round((time.perf_counter() - start_time) * 1000, 2),
        }


async def check_redis_health() -> Dict[str, Any]:
    """
    Executes a PING command on Redis.
    Returns status dict with response time.
    """
    start_time = time.perf_counter()
    try:
        redis_client = get_redis_client()
        res = await redis_client.ping()
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "healthy" if res else "unhealthy",
            "redis": "redis",
            "latency_ms": latency_ms,
        }
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "redis": "redis",
            "error": str(e),
            "latency_ms": round((time.perf_counter() - start_time) * 1000, 2),
        }


async def check_services_health() -> Dict[str, Any]:
    """
    Comprehensive health check combining PostgreSQL and Redis statuses.
    """
    db_health = await check_database_health()
    redis_health = await check_redis_health()
    
    is_healthy = (
        db_health.get("status") == "healthy" and 
        redis_health.get("status") == "healthy"
    )
    
    return {
        "status": "healthy" if is_healthy else "degraded",
        "database": db_health,
        "redis": redis_health,
    }
