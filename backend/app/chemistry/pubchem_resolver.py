"""
ChemRAG — PubChem PUG REST Resolver
====================================
Optional resolver for chemical structures and identifiers via PubChem PUG REST API.
Retrieves CID, canonical/isomeric SMILES, InChI, InChIKey, formula, molecular weight, and synonyms.
Includes:
- In-memory TTL caching
- Negative caching (caches 404/not found to protect API limits)
- Rate limiting (max 5 requests/sec complying with NCBI guidelines)
- Offline tolerance (core system works 100% offline when disabled or unreachable)
"""
from __future__ import annotations

import asyncio
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

PUBCHEM_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


@dataclass
class PubChemRecord:
    """Full resolved chemical metadata from PubChem."""
    cid: int
    canonical_smiles: str
    isomeric_smiles: Optional[str] = None
    inchi: Optional[str] = None
    inchi_key: Optional[str] = None
    iupac_name: Optional[str] = None
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    synonyms: List[str] = field(default_factory=list)


class PubChemResolver:
    """
    Client for resolving chemical identifiers using PubChem PUG REST API.
    """

    def __init__(
        self,
        enabled: bool = True,
        timeout: float = 10.0,
        rate_limit_delay_sec: float = 0.20,  # 5 req/s max
    ) -> None:
        self.enabled = enabled
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay_sec
        self._last_request_time = 0.0

        # Caching: key -> (record, expiry_timestamp)
        self._cache: Dict[str, Tuple[Optional[PubChemRecord], float]] = {}
        self.cache_ttl_seconds = 86400.0  # 24 hours
        self.negative_cache_ttl_seconds = 3600.0  # 1 hour for not-found

    async def _rate_limit(self) -> None:
        """Enforces spacing between calls to respect PubChem 5 req/s limit."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.monotonic()

    def _get_from_cache(self, key: str) -> Tuple[bool, Optional[PubChemRecord]]:
        """Check cache. Returns (is_cached, record_or_none)."""
        cached = self._cache.get(key)
        if cached:
            record, expiry = cached
            if time.time() < expiry:
                return True, record
            else:
                del self._cache[key]
        return False, None

    def _set_cache(self, key: str, record: Optional[PubChemRecord]) -> None:
        """Store in cache with appropriate positive or negative TTL."""
        ttl = self.cache_ttl_seconds if record else self.negative_cache_ttl_seconds
        self._cache[key] = (record, time.time() + ttl)

    async def resolve_by_name(self, name: str) -> Optional[PubChemRecord]:
        """Resolve a compound by chemical common or IUPAC name."""
        clean = name.strip()
        if not clean:
            return None
        cache_key = f"name:{clean.lower()}"
        is_hit, val = self._get_from_cache(cache_key)
        if is_hit:
            return val

        if not self.enabled:
            return None

        encoded = urllib.parse.quote(clean)
        url = (
            f"{PUBCHEM_BASE_URL}/compound/name/{encoded}/property/"
            "CanonicalSMILES,IsomericSMILES,InChI,InChIKey,IUPACName,MolecularFormula,MolecularWeight/JSON"
        )
        record = await self._fetch_compound_properties(url)
        self._set_cache(cache_key, record)
        return record

    async def resolve_by_smiles(self, smiles: str) -> Optional[PubChemRecord]:
        """Resolve a compound by SMILES string."""
        clean = smiles.strip()
        if not clean:
            return None
        cache_key = f"smiles:{clean}"
        is_hit, val = self._get_from_cache(cache_key)
        if is_hit:
            return val

        if not self.enabled:
            return None

        encoded = urllib.parse.quote(clean)
        url = (
            f"{PUBCHEM_BASE_URL}/compound/smiles/{encoded}/property/"
            "CanonicalSMILES,IsomericSMILES,InChI,InChIKey,IUPACName,MolecularFormula,MolecularWeight/JSON"
        )
        record = await self._fetch_compound_properties(url)
        self._set_cache(cache_key, record)
        return record

    async def resolve_by_inchikey(self, inchi_key: str) -> Optional[PubChemRecord]:
        """Resolve a compound by 27-character InChIKey."""
        clean = inchi_key.strip()
        if not clean:
            return None
        cache_key = f"inchikey:{clean}"
        is_hit, val = self._get_from_cache(cache_key)
        if is_hit:
            return val

        if not self.enabled:
            return None

        url = (
            f"{PUBCHEM_BASE_URL}/compound/inchikey/{clean}/property/"
            "CanonicalSMILES,IsomericSMILES,InChI,InChIKey,IUPACName,MolecularFormula,MolecularWeight/JSON"
        )
        record = await self._fetch_compound_properties(url)
        self._set_cache(cache_key, record)
        return record

    async def _fetch_compound_properties(self, url: str) -> Optional[PubChemRecord]:
        """Execute HTTP request against PubChem with retries and rate limiting."""
        await self._rate_limit()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for attempt in range(3):
                    try:
                        response = await client.get(url)
                        if response.status_code == 200:
                            data = response.json()
                            props_list = data.get("PropertyTable", {}).get("Properties", [])
                            if not props_list:
                                return None
                            p = props_list[0]
                            return PubChemRecord(
                                cid=int(p.get("CID", 0)),
                                canonical_smiles=p.get("CanonicalSMILES", ""),
                                isomeric_smiles=p.get("IsomericSMILES"),
                                inchi=p.get("InChI"),
                                inchi_key=p.get("InChIKey"),
                                iupac_name=p.get("IUPACName"),
                                molecular_formula=p.get("MolecularFormula"),
                                molecular_weight=float(p.get("MolecularWeight", 0.0)) if p.get("MolecularWeight") else None,
                            )
                        elif response.status_code == 404:
                            # Not found in PubChem -> negative cache
                            return None
                        elif response.status_code in (503, 429):
                            await asyncio.sleep(0.5 * (attempt + 1))
                            continue
                        else:
                            return None
                    except (httpx.TimeoutException, httpx.NetworkError):
                        if attempt == 2:
                            return None
                        await asyncio.sleep(0.5)

        except Exception as exc:
            logger.info("PubChem resolution offline or failed", error=str(exc))
            return None

        return None
