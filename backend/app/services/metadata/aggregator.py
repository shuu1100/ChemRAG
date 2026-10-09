"""
ChemRAG — Metadata Aggregator Orchestrator
===========================================
Unified orchestrator for querying scholarly metadata across multiple external providers
(Crossref, OpenAlex, Semantic Scholar, PubMed/NCBI, arXiv).
Includes:
- Fallback orchestration
- Provider toggle controls
- Offline resilience
- Cached metadata lookup
"""
from __future__ import annotations

import asyncio
from typing import List, Optional

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger
from backend.app.services.metadata.arxiv import ArXivProvider
from backend.app.services.metadata.crossref import CrossrefProvider
from backend.app.services.metadata.models import PublicationMetadata
from backend.app.services.metadata.openalex import OpenAlexProvider
from backend.app.services.metadata.pubmed import PubMedProvider
from backend.app.services.metadata.semantic_scholar import SemanticScholarProvider

logger = get_logger(__name__)


class MetadataAggregator:
    """Orchestrates metadata resolution across external providers."""

    def __init__(
        self,
        enabled: bool = True,
        crossref_enabled: bool = True,
        openalex_enabled: bool = True,
        semantic_scholar_enabled: bool = True,
        pubmed_enabled: bool = True,
        arxiv_enabled: bool = True,
    ) -> None:
        self.enabled = enabled
        self.crossref = CrossrefProvider(enabled=enabled and crossref_enabled)
        self.openalex = OpenAlexProvider(enabled=enabled and openalex_enabled)
        self.semantic_scholar = SemanticScholarProvider(enabled=enabled and semantic_scholar_enabled)
        self.pubmed = PubMedProvider(enabled=enabled and pubmed_enabled)
        self.arxiv = ArXivProvider(enabled=enabled and arxiv_enabled)

        self.providers = [
            self.crossref,
            self.openalex,
            self.semantic_scholar,
            self.pubmed,
            self.arxiv,
        ]

    async def fetch_by_doi(self, doi: str) -> Optional[PublicationMetadata]:
        """Fetch metadata by DOI, trying providers sequentially until a hit is found."""
        clean_doi = doi.strip()
        if not clean_doi or not self.enabled:
            return None

        for provider in self.providers:
            if not provider.enabled:
                continue
            try:
                meta = await provider.fetch_by_doi(clean_doi)
                if meta:
                    logger.info("Found metadata by DOI", doi=clean_doi, provider=provider.provider_name)
                    return meta
            except Exception as exc:
                logger.warning(
                    "Provider fetch failed", provider=provider.provider_name, doi=clean_doi, error=str(exc)
                )

        return None

    async def search(self, query: str, limit: int = 5) -> List[PublicationMetadata]:
        """Search literature metadata across enabled providers."""
        clean_q = query.strip()
        if not clean_q or not self.enabled:
            return []

        active_providers = [p for p in self.providers if p.enabled]
        if not active_providers:
            return []

        # Execute searches concurrently across enabled providers
        tasks = [provider.search(clean_q, limit=limit) for provider in active_providers]
        results_nested = await asyncio.gather(*tasks, return_exceptions=True)

        combined: List[PublicationMetadata] = []
        seen_titles = set()

        for res in results_nested:
            if isinstance(res, list):
                for meta in res:
                    norm_title = meta.title.lower().strip()
                    if norm_title not in seen_titles:
                        seen_titles.add(norm_title)
                        combined.append(meta)

        return combined[:limit]
