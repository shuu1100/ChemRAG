"""
ChemRAG — PubMed/NCBI Scientific Metadata Provider
====================================================
Fetches biomedical and chemical literature metadata via NCBI E-utilities API.
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

PUBMED_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


class PubMedProvider(BaseMetadataProvider):
    def __init__(self, enabled: bool = True, timeout: float = 15.0) -> None:
        super().__init__(provider_name="pubmed", enabled=enabled, timeout=timeout, rate_limit_delay_sec=0.34)  # 3 req/s limit

    async def fetch_by_doi(self, doi: str) -> Optional[PublicationMetadata]:
        clean_doi = doi.strip().replace("https://doi.org/", "")
        if not clean_doi:
            return None

        cache_key = f"pubmed:doi:{clean_doi.lower()}"
        is_hit, cached_meta = self._get_from_cache(cache_key)
        if is_hit:
            return cached_meta

        if not self.enabled:
            return None

        pmid = await self._search_pmid_by_doi(clean_doi)
        if not pmid:
            self._set_cache(cache_key, None)
            return None

        meta = await self.fetch_by_pmid(pmid)
        if meta:
            meta.doi = clean_doi
        self._set_cache(cache_key, meta)
        return meta

    async def fetch_by_pmid(self, pmid: str) -> Optional[PublicationMetadata]:
        clean_pmid = pmid.strip()
        if not clean_pmid or not self.enabled:
            return None

        await self._rate_limit()
        url = f"{PUBMED_ESUMMARY_URL}?db=pubmed&id={clean_pmid}&retmode=json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    result_data = res.json().get("result", {}).get(clean_pmid, {})
                    if result_data:
                        title = result_data.get("title", "").rstrip(".")
                        authors = [a.get("name", "") for a in result_data.get("authors", []) if a.get("name")]
                        journal = result_data.get("source")
                        pub_date = result_data.get("pubdate")
                        pub_year = None
                        if pub_date and len(pub_date) >= 4 and pub_date[:4].isdigit():
                            pub_year = int(pub_date[:4])

                        # Extract DOI if present in articleids
                        doi = None
                        for aid in result_data.get("articleids", []):
                            if aid.get("idtype") == "doi":
                                doi = aid.get("value")

                        return PublicationMetadata(
                            title=title,
                            authors=authors,
                            doi=doi,
                            publication_date=pub_date,
                            publication_year=pub_year,
                            journal=journal,
                            venue=journal,
                            provider="pubmed",
                            external_url=f"https://pubmed.ncbi.nlm.nih.gov/{clean_pmid}/",
                        )
        except Exception as exc:
            logger.info("PubMed E-summary offline or failed", pmid=clean_pmid, error=str(exc))
            return None

        return None

    async def search(self, query: str, limit: int = 5) -> List[PublicationMetadata]:
        clean_q = query.strip()
        if not clean_q or not self.enabled:
            return []

        await self._rate_limit()
        encoded = urllib.parse.quote(clean_q)
        url = f"{PUBMED_ESEARCH_URL}?db=pubmed&term={encoded}&retmax={limit}&retmode=json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    id_list = res.json().get("esearchresult", {}).get("idlist", [])
                    results = []
                    for pmid in id_list:
                        meta = await self.fetch_by_pmid(pmid)
                        if meta:
                            results.append(meta)
                    return results
        except Exception as exc:
            logger.info("PubMed search offline or failed", query=clean_q, error=str(exc))

        return []

    async def _search_pmid_by_doi(self, doi: str) -> Optional[str]:
        await self._rate_limit()
        encoded = urllib.parse.quote(f"{doi}[location id]")
        url = f"{PUBMED_ESEARCH_URL}?db=pubmed&term={encoded}&retmode=json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    id_list = res.json().get("esearchresult", {}).get("idlist", [])
                    if id_list:
                        return id_list[0]
        except Exception:
            return None
        return None
