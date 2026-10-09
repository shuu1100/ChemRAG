"""
ChemRAG — Scientific Publication Metadata Models
================================================
Standardized metadata representation across external scholarly providers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class PublicationMetadata:
    """Unified publication metadata payload."""
    title: str
    authors: List[str] = field(default_factory=list)
    doi: Optional[str] = None
    publication_date: Optional[str] = None
    publication_year: Optional[int] = None
    journal: Optional[str] = None
    abstract: Optional[str] = None
    citation_count: Optional[int] = None
    venue: Optional[str] = None
    provider: str = "unknown"
    external_url: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "authors": self.authors,
            "doi": self.doi,
            "publication_date": self.publication_date,
            "publication_year": self.publication_year,
            "journal": self.journal,
            "abstract": self.abstract,
            "citation_count": self.citation_count,
            "venue": self.venue,
            "provider": self.provider,
            "external_url": self.external_url,
            "keywords": self.keywords,
            "fetched_at": self.fetched_at.isoformat(),
        }
