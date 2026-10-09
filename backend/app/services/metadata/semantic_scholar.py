"""
ChemRAG — Semantic Scholar Scientific Metadata Provider
=========================================================
Fetches paper metadata via Semantic Scholar Academic Graph API (https://api.semanticscholar.org/).
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

S2_BASE_URL = "https://api.semanticscholar.org/graph/v1/paper"


class SemanticScholarProvider(BaseMetadataProvider):
    def __init__(self, enabled: bool = True, timeout: float = 15.0) -> None:
        super().__init__(provider_name="semantic_scholar", enabled=enabled, timeout=timeout, rate_limit_delay_sec=0.5)

    async def fetch_by_doi(self, doi: str) -> Optional[PublicationMetadata]:
        clean_doi = doi.strip().replace("https://doi.org/", "")
        if not clean_doi:
            return None

        cache_key = f"s2:doi:{clean_doi.lower()}"
        is_hit, cached_meta = self._get_from_cache(cache_key)
        if is_hit:
            return cached_meta

        if not self.enabled:
            return None

        await self._rate_limit()
        url = f"{S2_BASE_URL}/DOI:{urllib.parse.quote(clean_doi)}?fields=title,authors,year,venue,publicationDate,abstract,citationCount,externalIds,url"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    meta = self._parse_paper(res.json())
                    self._set_cache(cache_key, meta)
                    return meta
                elif res.status_code == 404:
                    self._set_cache(cache_key, None)
                    return None
        except Exception as exc:
            logger.info("Semantic Scholar API offline or timed out", doi=clean_doi, error=str(exc))
            return None

        return None

    async def search(self, query: str, limit: int = 5) -> List[PublicationMetadata]:
        clean_q = query.strip()
        if not clean_q or not self.enabled:
            return []

        await self._rate_limit()
        encoded = urllib.parse.quote(clean_q)
        url = f"{S2_BASE_URL}/search?query={encoded}&limit={limit}&fields=title,authors,year,venue,publicationDate,abstract,citationCount,externalIds,url"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json().get("data", [])
                    return [self._parse_paper(p) for p in data if p]
        except Exception as exc:
            logger.info("Semantic Scholar search offline or failed", query=clean_q, error=str(exc))

        return []

    def _parse_paper(self, paper: dict) -> PublicationMetadata:
        title = paper.get("title") or "Untitled Publication"
        authors = [a.get("name", "") for a in paper.get("authors", []) if a.get("name")]
        ext_ids = paper.get("externalIds") or {}
        doi = ext_ids.get("DOI")

        return PublicationMetadata(
            title=title,
            authors=authors,
            doi=doi,
            publication_date=paper.get("publicationDate"),
            publication_year=paper.get("year"),
            journal=paper.get("venue"),
            abstract=paper.get("abstract"),
            citation_count=paper.get("citationCount"),
            venue=paper.get("venue"),
            provider="semantic_scholar",
            external_url=paper.get("url") or (f"https://doi.org/{doi}" if doi else None),
        )
