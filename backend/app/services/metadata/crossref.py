"""
ChemRAG — Crossref Scientific Metadata Provider
================================================
Fetches publication metadata via Crossref REST API (https://api.crossref.org/).
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

CROSSREF_BASE_URL = "https://api.crossref.org/works"


class CrossrefProvider(BaseMetadataProvider):
    def __init__(self, enabled: bool = True, timeout: float = 15.0) -> None:
        super().__init__(provider_name="crossref", enabled=enabled, timeout=timeout, rate_limit_delay_sec=0.2)

    async def fetch_by_doi(self, doi: str) -> Optional[PublicationMetadata]:
        clean_doi = doi.strip().replace("https://doi.org/", "")
        if not clean_doi:
            return None

        cache_key = f"crossref:doi:{clean_doi.lower()}"
        is_hit, cached_meta = self._get_from_cache(cache_key)
        if is_hit:
            return cached_meta

        if not self.enabled:
            return None

        await self._rate_limit()
        url = f"{CROSSREF_BASE_URL}/{urllib.parse.quote(clean_doi)}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"User-Agent": "ChemRAG/0.1.0 (mailto:support@chemrag.org)"}
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    data = res.json().get("message", {})
                    meta = self._parse_item(data)
                    self._set_cache(cache_key, meta)
                    return meta
                elif res.status_code == 404:
                    self._set_cache(cache_key, None)
                    return None
        except Exception as exc:
            logger.info("Crossref API offline or timed out", doi=clean_doi, error=str(exc))
            return None

        return None

    async def search(self, query: str, limit: int = 5) -> List[PublicationMetadata]:
        clean_q = query.strip()
        if not clean_q or not self.enabled:
            return []

        await self._rate_limit()
        encoded = urllib.parse.quote(clean_q)
        url = f"{CROSSREF_BASE_URL}?query={encoded}&rows={limit}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"User-Agent": "ChemRAG/0.1.0 (mailto:support@chemrag.org)"}
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    items = res.json().get("message", {}).get("items", [])
                    return [self._parse_item(item) for item in items if item]
        except Exception as exc:
            logger.info("Crossref search offline or failed", query=clean_q, error=str(exc))

        return []

    def _parse_item(self, item: dict) -> PublicationMetadata:
        title = " ".join(item.get("title", [])) if item.get("title") else "Untitled Publication"
        authors = []
        for a in item.get("author", []):
            given = a.get("given", "")
            family = a.get("family", "")
            name = f"{given} {family}".strip()
            if name:
                authors.append(name)

        pub_year = None
        issued = item.get("issued", {}).get("date-parts", [[]])[0]
        if issued and len(issued) > 0:
            pub_year = issued[0]

        journal_list = item.get("container-title", [])
        journal = journal_list[0] if journal_list else None

        doi = item.get("DOI")
        url = item.get("URL") or (f"https://doi.org/{doi}" if doi else None)

        return PublicationMetadata(
            title=title,
            authors=authors,
            doi=doi,
            publication_year=pub_year,
            journal=journal,
            citation_count=item.get("is-referenced-by-count"),
            venue=journal,
            provider="crossref",
            external_url=url,
        )
