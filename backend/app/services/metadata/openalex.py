"""
ChemRAG — OpenAlex Scientific Metadata Provider
================================================
Fetches paper metadata via OpenAlex API (https://api.openalex.org/).
Does NOT download copyrighted full text.
"""
from __future__ import annotations

import urllib.parse
from typing import List, Optional

import httpx

from backend.app.core.logging import get_logger
from backend.app.services.metadata.base import BaseMetadataProvider
from backend.app.services.metadata.models import PublicationMetadata

logger = get_logger(__name__)

OPENALEX_BASE_URL = "https://api.openalex.org/works"


class OpenAlexProvider(BaseMetadataProvider):
    def __init__(self, enabled: bool = True, timeout: float = 15.0) -> None:
        super().__init__(provider_name="openalex", enabled=enabled, timeout=timeout, rate_limit_delay_sec=0.2)

    async def fetch_by_doi(self, doi: str) -> Optional[PublicationMetadata]:
        clean_doi = doi.strip().replace("https://doi.org/", "")
        if not clean_doi:
            return None

        cache_key = f"openalex:doi:{clean_doi.lower()}"
        is_hit, cached_meta = self._get_from_cache(cache_key)
        if is_hit:
            return cached_meta

        if not self.enabled:
            return None

        await self._rate_limit()
        url = f"{OPENALEX_BASE_URL}/https://doi.org/{urllib.parse.quote(clean_doi)}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    meta = self._parse_work(res.json())
                    self._set_cache(cache_key, meta)
                    return meta
                elif res.status_code == 404:
                    self._set_cache(cache_key, None)
                    return None
        except Exception as exc:
            logger.info("OpenAlex API offline or timed out", doi=clean_doi, error=str(exc))
            return None

        return None

    async def search(self, query: str, limit: int = 5) -> List[PublicationMetadata]:
        clean_q = query.strip()
        if not clean_q or not self.enabled:
            return []

        await self._rate_limit()
        encoded = urllib.parse.quote(clean_q)
        url = f"{OPENALEX_BASE_URL}?search={encoded}&per_page={limit}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    results = res.json().get("results", [])
                    return [self._parse_work(w) for w in results if w]
        except Exception as exc:
            logger.info("OpenAlex search offline or failed", query=clean_q, error=str(exc))

        return []

    def _parse_work(self, work: dict) -> PublicationMetadata:
        title = work.get("title") or "Untitled Publication"
        authors = [
            auth.get("author", {}).get("display_name", "")
            for auth in work.get("authorships", [])
            if auth.get("author", {}).get("display_name")
        ]

        doi_url = work.get("doi")
        doi = doi_url.replace("https://doi.org/", "") if doi_url else None
        pub_year = work.get("publication_year")
        pub_date = work.get("publication_date")

        primary_loc = work.get("primary_location") or {}
        source = primary_loc.get("source") or {}
        venue = source.get("display_name")

        abstract = None
        inv_idx = work.get("abstract_inverted_index")
        if inv_idx and isinstance(inv_idx, dict):
            # Reconstruct abstract text from OpenAlex inverted index
            words = []
            for word, pos_list in inv_idx.items():
                for pos in pos_list:
                    words.append((pos, word))
            words.sort(key=lambda x: x[0])
            abstract = " ".join([w[1] for w in words])

        return PublicationMetadata(
            title=title,
            authors=authors,
            doi=doi,
            publication_date=pub_date,
            publication_year=pub_year,
            journal=venue,
            abstract=abstract,
            citation_count=work.get("cited_by_count"),
            venue=venue,
            provider="openalex",
            external_url=doi_url or work.get("id"),
        )
