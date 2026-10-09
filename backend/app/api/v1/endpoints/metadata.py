"""
ChemRAG — Scientific Metadata API Endpoints
============================================
Endpoints:
- POST /metadata/doi      (Fetch metadata for a DOI from external providers)
- POST /metadata/search   (Search scholarly publication metadata)
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from backend.app.services.metadata.aggregator import MetadataAggregator

router = APIRouter()
metadata_aggregator = MetadataAggregator()


class LookupDoiRequest(BaseModel):
    doi: str


class SearchMetadataRequest(BaseModel):
    query: str
    limit: int = 5


class MetadataResponse(BaseModel):
    title: str
    authors: List[str]
    doi: Optional[str] = None
    publication_date: Optional[str] = None
    publication_year: Optional[int] = None
    journal: Optional[str] = None
    abstract: Optional[str] = None
    citation_count: Optional[int] = None
    venue: Optional[str] = None
    provider: str
    external_url: Optional[str] = None


@router.post(
    "/doi",
    response_model=Optional[MetadataResponse],
    summary="Lookup publication metadata by DOI",
)
async def lookup_doi(payload: LookupDoiRequest) -> Optional[MetadataResponse]:
    """Fetch metadata by DOI across Crossref, OpenAlex, Semantic Scholar, PubMed, and arXiv."""
    meta = await metadata_aggregator.fetch_by_doi(payload.doi)
    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Publication metadata for DOI '{payload.doi}' not found or providers offline.",
        )
    return MetadataResponse(**meta.to_dict())


@router.post(
    "/search",
    response_model=List[MetadataResponse],
    summary="Search scholarly publication metadata",
)
async def search_metadata(payload: SearchMetadataRequest) -> List[MetadataResponse]:
    """Search scientific literature metadata across configured external providers."""
    items = await metadata_aggregator.search(payload.query, limit=payload.limit)
    return [MetadataResponse(**item.to_dict()) for item in items]
