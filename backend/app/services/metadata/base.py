"""
ChemRAG — Base Metadata Provider Abstraction
=============================================
Abstract base class for all external scientific metadata providers.
Includes caching, rate limiting, and offline tolerance.
"""
from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

from backend.app.core.logging import get_logger
from backend.app.services.metadata.models import PublicationMetadata

logger = get_logger(__name__)


class BaseMetadataProvider(ABC):
    """Abstract base class for scientific metadata providers."""

    def __init__(
        self,
        provider_name: str,
        enabled: bool = True,
        timeout: float = 15.0,
        rate_limit_delay_sec: float = 0.5,
    ) -> None:
        self.provider_name = provider_name
        self.enabled = enabled
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay_sec
        self._last_call_time = 0.0

        # Caching: cache_key -> (PublicationMetadata | None, expiry_timestamp)
        self._cache: Dict[str, Tuple[Optional[PublicationMetadata], float]] = {}
        self.cache_ttl_seconds = 86400.0  # 24 hours
        self.negative_cache_ttl_seconds = 3600.0  # 1 hour for 404s

    async def _rate_limit(self) -> None:
        """Enforces spacing between calls to respect provider API guidelines."""
        now = time.monotonic()
        elapsed = now - self._last_call_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self._last_call_time = time.monotonic()

    def _get_from_cache(self, key: str) -> Tuple[bool, Optional[PublicationMetadata]]:
        cached = self._cache.get(key)
        if cached:
            meta, expiry = cached
            if time.time() < expiry:
                return True, meta
            else:
                del self._cache[key]
        return False, None

    def _set_cache(self, key: str, meta: Optional[PublicationMetadata]) -> None:
        ttl = self.cache_ttl_seconds if meta else self.negative_cache_ttl_seconds
        self._cache[key] = (meta, time.time() + ttl)

    @abstractmethod
    async def fetch_by_doi(self, doi: str) -> Optional[PublicationMetadata]:
        """Fetch metadata by Digital Object Identifier (DOI)."""
        pass

    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> List[PublicationMetadata]:
        """Search literature metadata by keywords or title query."""
        pass
