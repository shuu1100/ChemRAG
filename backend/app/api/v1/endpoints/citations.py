"""
ChemRAG — Citations & Provenance API Endpoints
================================================
Exposes Phase 13 capabilities:
- Citation Engine assignment & context prompt generation
- Citation Validation & claim-entailment checking
- PDF.js Evidence Mapping for interactive bounding box overlays
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.citations.engine import CitationEngine
from backend.app.citations.evidence_mapper import EvidenceMapper
from backend.app.citations.models import (
    CitationMetadata,
    CitationValidationResult,
    EvidenceMappingRequest,
    EvidenceMappingResponse,
)
from backend.app.citations.validator import CitationValidator

logger = logging.getLogger(__name__)
router = APIRouter()

citation_engine = CitationEngine()
citation_validator = CitationValidator()
evidence_mapper = EvidenceMapper()


class AssignCitationsRequest(BaseModel):
    """Input payload containing evidence chunks to assign stable citations to."""
    chunks: List[Dict[str, Any]] = Field(description="List of chunk dictionaries with chunk_id, document_id, content, etc.")


class AssignCitationsResponse(BaseModel):
    """Response containing assigned citation objects and LLM formatted prompt context."""
    citations: List[CitationMetadata]
    llm_context_text: str


class ValidateCitationRequest(BaseModel):
    """Payload for post-generation response validation."""
    generated_text: str = Field(description="LLM response text to validate")
    valid_citations: List[CitationMetadata] = Field(description="List of active citations in context")


@router.post(
    "/assign",
    response_model=AssignCitationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign stable citations",
    description="Assigns CIT-xxx identifiers to evidence chunks and formats LLM context prompt.",
)
async def assign_citations(req: AssignCitationsRequest) -> AssignCitationsResponse:
    """Assign stable citations to retrieved chunks."""
    try:
        from backend.app.retrieval.models import ScoredChunk

        scored_chunks: List[ScoredChunk] = []
        for c in req.chunks:
            chunk_id = uuid.UUID(str(c.get("chunk_id", uuid.uuid4())))
            doc_id = uuid.UUID(str(c.get("document_id", uuid.uuid4())))
            content = str(c.get("content", c.get("text", "")))
            score = float(c.get("score", 1.0))
            page = c.get("page_number")
            bbox = c.get("bbox")
            meta = c.get("metadata", {})

            sc = ScoredChunk(
                chunk_id=chunk_id,
                document_id=doc_id,
                content=content,
                score=score,
                page_number=page,
                bbox=bbox,
                metadata=meta,
            )
            scored_chunks.append(sc)

        citations = citation_engine.assign_citations(scored_chunks)
        llm_context = citation_engine.format_context_with_citations(citations)

        return AssignCitationsResponse(
            citations=citations,
            llm_context_text=llm_context,
        )
    except Exception as exc:
        logger.error(f"Error in assign_citations endpoint: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to assign citations: {str(exc)}",
        )


@router.post(
    "/validate",
    response_model=CitationValidationResult,
    status_code=status.HTTP_200_OK,
    summary="Validate citations and claims",
    description="Extracts claims and checks citation validity, claim entailment, and hallucinated DOIs.",
)
async def validate_citations(req: ValidateCitationRequest) -> CitationValidationResult:
    """Validate generated response against active context citations."""
    try:
        result = citation_validator.validate_response(
            generated_text=req.generated_text,
            valid_citations=req.valid_citations,
        )
        return result
    except Exception as exc:
        logger.error(f"Error in validate_citations endpoint: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to validate citations: {str(exc)}",
        )


@router.post(
    "/evidence",
    response_model=EvidenceMappingResponse,
    status_code=status.HTTP_200_OK,
    summary="Map citation to PDF.js viewport coordinates",
    description="Calculates viewport overlay pixel & percentage coordinates for PDF.js visualization.",
)
async def map_evidence_coordinates(
    req: EvidenceMappingRequest,
    citation: CitationMetadata,
) -> EvidenceMappingResponse:
    """Convert citation bounding box to PDF.js viewport display overlay."""
    try:
        response = evidence_mapper.map_evidence(citation, req)
        return response
    except Exception as exc:
        logger.error(f"Error in map_evidence_coordinates endpoint: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to map evidence coordinates: {str(exc)}",
        )
