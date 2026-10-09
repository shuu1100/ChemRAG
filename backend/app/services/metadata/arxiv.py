"""
ChemRAG — arXiv Scientific Preprint Metadata Provider
======================================================
Fetches preprint metadata via arXiv REST API (http://export.arxiv.org/api/query).
Does NOT download copyrighted full text.
"""
from __future__ import annotations

import urllib.parse
import xml.etree.ElementTree as ET
from typing import List, Optional

import httpx

from backend.app.core.logging import get_logger
from backend.app.services.metadata.base import BaseMetadataProvider
from backend.app.services.metadata.models import PublicationMetadata

logger = get_logger(__name__)

ARXIV_BASE_URL = "http://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


class ArXivProvider(BaseMetadataProvider):
    def __init__(self, enabled: bool = True, timeout: float = 15.0) -> None:
        super().__init__(provider_name="arxiv", enabled=enabled, timeout=timeout, rate_limit_delay_sec=1.0)  # 3s recommended

    async def fetch_by_doi(self, doi: str) -> Optional[PublicationMetadata]:
        clean_doi = doi.strip().replace("https://doi.org/", "")
        if not clean_doi:
            return None

        cache_key = f"arxiv:doi:{clean_doi.lower()}"
        is_hit, cached_meta = self._get_from_cache(cache_key)
        if is_hit:
            return cached_meta

        if not self.enabled:
            return None

        results = await self.search(f"doi:{clean_doi}", limit=1)
        meta = results[0] if results else None
        self._set_cache(cache_key, meta)
        return meta

    async def fetch_by_arxiv_id(self, arxiv_id: str) -> Optional[PublicationMetadata]:
        clean_id = arxiv_id.strip()
        if not clean_id or not self.enabled:
            return None

        results = await self.search(f"id:{clean_id}", limit=1)
        return results[0] if results else None

    async def search(self, query: str, limit: int = 5) -> List[PublicationMetadata]:
        clean_q = query.strip()
        if not clean_q or not self.enabled:
            return []

        await self._rate_limit()
        encoded = urllib.parse.quote(clean_q)
        url = f"{ARXIV_BASE_URL}?search_query=all:{encoded}&max_results={limit}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    return self._parse_atom_feed(res.text)
        except Exception as exc:
            logger.info("arXiv API search offline or failed", query=clean_q, error=str(exc))

        return []

    def _parse_atom_feed(self, xml_text: str) -> List[PublicationMetadata]:
        results: List[PublicationMetadata] = []
        try:
            root = ET.fromstring(xml_text)
            for entry in root.findall("atom:entry", ATOM_NS):
                title_elem = entry.find("atom:title", ATOM_NS)
                title = title_elem.text.strip().replace("\n", " ") if title_elem is not None and title_elem.text else "Untitled Preprint"

                authors = []
                for author_elem in entry.findall("atom:author", ATOM_NS):
                    name_elem = author_elem.find("atom:name", ATOM_NS)
                    if name_elem is not None and name_elem.text:
                        authors.append(name_elem.text.strip())

                pub_date_elem = entry.find("atom:published", ATOM_NS)
                pub_date = pub_date_elem.text.strip() if pub_date_elem is not None and pub_date_elem.text else None
                pub_year = int(pub_date[:4]) if pub_date and len(pub_date) >= 4 and pub_date[:4].isdigit() else None

                summary_elem = entry.find("atom:summary", ATOM_NS)
                abstract = summary_elem.text.strip().replace("\n", " ") if summary_elem is not None and summary_elem.text else None

                id_elem = entry.find("atom:id", ATOM_NS)
                arxiv_url = id_elem.text.strip() if id_elem is not None and id_elem.text else None

                doi_elem = entry.find("arxiv:doi", ATOM_NS)
                doi = doi_elem.text.strip() if doi_elem is not None and doi_elem.text else None

                results.append(
                    PublicationMetadata(
                        title=title,
                        authors=authors,
                        doi=doi,
                        publication_date=pub_date,
                        publication_year=pub_year,
                        journal="arXiv preprint",
                        abstract=abstract,
                        venue="arXiv",
                        provider="arxiv",
                        external_url=arxiv_url,
                    )
                )
        except Exception as exc:
            logger.info("Error parsing arXiv XML response", error=str(exc))

        return results
