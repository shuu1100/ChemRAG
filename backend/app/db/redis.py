"""
ChemRAG — Redis Client
=======================
Provides a singleton async Redis connection with:
- Health check (PING)
- JSON-serialized get/set/delete
- Deterministic cache key helpers
- Configurable TTL support
- Clean shutdown
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

_redis_client: Redis | None = None


def get_redis_client() -> Redis:
    """Return the singleton Redis client. Raises if not initialized."""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        rc = settings.redis
        _redis_client = aioredis.Redis(
            host=rc.host,
            port=rc.port,
            db=rc.db,
            password=rc.password.get_secret_value() if rc.password else None,
            decode_responses=rc.decode_responses,
            socket_timeout=rc.socket_timeout,
            socket_connect_timeout=rc.socket_connect_timeout,
            max_connections=rc.max_connections,
        )
    return _redis_client


async def close_redis() -> None:
    """Call during application shutdown to cleanly close the Redis connection."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis client closed")


# ── Health check ──────────────────────────────────────────────────────────────


async def redis_ping() -> bool:
    """Return True if Redis responds to PING."""
    try:
        client = get_redis_client()
        pong = await client.ping()
        return bool(pong)
    except (RedisConnectionError, RedisTimeoutError, OSError) as exc:
        logger.warning("Redis PING failed: %s", exc)
        return False


# ── Core cache operations ─────────────────────────────────────────────────────


async def cache_get(key: str) -> Any | None:
    """
    Retrieve a JSON-decoded value from Redis.
    Returns None on cache miss or connection failure.
    """
    try:
        client = get_redis_client()
        raw = await client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except (RedisConnectionError, RedisTimeoutError) as exc:
        logger.warning("Redis GET failed for key=%s: %s", key, exc)
        return None
    except json.JSONDecodeError as exc:
        logger.warning("Redis: failed to decode JSON for key=%s: %s", key, exc)
        return None


async def cache_set(key: str, value: Any, ttl_seconds: int | None = None) -> bool:
    """
    Store a JSON-encoded value in Redis with optional TTL.
    Returns True on success, False on failure.
    """
    try:
        client = get_redis_client()
        serialized = json.dumps(value, default=str)
        if ttl_seconds is not None:
            await client.setex(key, ttl_seconds, serialized)
        else:
            await client.set(key, serialized)
        return True
    except (RedisConnectionError, RedisTimeoutError) as exc:
        logger.warning("Redis SET failed for key=%s: %s", key, exc)
        return False
    except (TypeError, ValueError) as exc:
        logger.warning("Redis SET: JSON serialization failed for key=%s: %s", key, exc)
        return False


async def cache_delete(key: str) -> bool:
    """Delete a key from Redis. Returns True if key was deleted."""
    try:
        client = get_redis_client()
        result = await client.delete(key)
        return result > 0
    except (RedisConnectionError, RedisTimeoutError) as exc:
        logger.warning("Redis DELETE failed for key=%s: %s", key, exc)
        return False


async def cache_exists(key: str) -> bool:
    """Check if a key exists in Redis."""
    try:
        client = get_redis_client()
        return bool(await client.exists(key))
    except (RedisConnectionError, RedisTimeoutError):
        return False


# ── Deterministic cache key helpers ──────────────────────────────────────────


def pubchem_cache_key(identifier_type: str, identifier: str) -> str:
    """
    Build a deterministic PubChem cache key.
    Example: chemrag:pubchem:name:aspirin
    """
    return f"chemrag:pubchem:{identifier_type}:{identifier.lower().strip()}"


def crossref_cache_key(doi: str) -> str:
    """Build a deterministic Crossref/DOI cache key."""
    return f"chemrag:crossref:doi:{doi.lower().strip()}"


def europepmc_cache_key(query_hash: str) -> str:
    """Build a deterministic EuropePMC cache key."""
    return f"chemrag:europepmc:query:{query_hash}"


def ncbi_cache_key(identifier: str) -> str:
    """Build a deterministic NCBI/PubMed cache key."""
    return f"chemrag:ncbi:{identifier.lower().strip()}"


def semantic_scholar_cache_key(query_hash: str) -> str:
    """Build a deterministic Semantic Scholar cache key."""
    return f"chemrag:semanticscholar:{query_hash}"
