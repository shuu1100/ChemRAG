"""
ChemRAG — Citations & Provenance Data Models
=============================================
Defines structured schemas for:
- Stable citation identifiers (e.g., [CIT-001])
- Citation provenance metadata (document, version, page, bbox, section)
- Claim verification & citation validation results
- PDF.js viewport coordinate evidence mapping
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CitationMetadata(BaseModel):
    """
    Metadata binding a stable citation identifier (e.g., CIT-001) to its exact source origin.
    """
    citation_id: str = Field(description="Stable citation identifier, e.g. CIT-001")
    chunk_id: uuid.UUID = Field(description="Database UUID of source chunk")
    document_id: uuid.UUID = Field(description="Database UUID of source document")
    document_title: str = Field(default="Scientific Document", description="Document title")
    document_version_id: Optional[uuid.UUID] = Field(default=None, description="Document version UUID")
    page_number: Optional[int] = Field(default=None, description="1-indexed page number")
    section_title: Optional[str] = Field(default=None, description="Section heading")
    bbox: Optional[Dict[str, float]] = Field(
        default=None, description="Bounding box dict with x0, y0, x1, y1 in PDF points"
    )
    source_asset_id: Optional[uuid.UUID] = Field(default=None, description="Source PDF/image asset UUID")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Retrieval / extraction confidence")
    raw_text: str = Field(description="Verbatim chunk text snippet")
    doi: Optional[str] = Field(default=None, description="Document DOI if available")
    extra_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional provenance fields")


class ClaimVerificationResult(BaseModel):
    """
    Verification analysis for a single factual claim extracted from generated text.
    """
    claim_text: str = Field(description="The extracted factual claim sentence")
    cited_ids: List[str] = Field(default_factory=list, description="Citation IDs associated with claim")
    is_supported: bool = Field(description="True if cited evidence supports the claim")
    support_score: float = Field(default=0.0, ge=0.0, le=1.0, description="NLI / semantic entailment score")
    reasoning: str = Field(default="", description="Explanatory justification for entailment verdict")
    is_uncited: bool = Field(default=False, description="True if claim contains facts but lacks citation")


class CitationValidationResult(BaseModel):
    """
    Comprehensive post-generation citation validation report.
    """
    is_valid: bool = Field(description="True if all citations are valid and claims supported")
    total_claims_count: int = Field(default=0, ge=0)
    supported_claims_count: int = Field(default=0, ge=0)
    unsupported_claims_count: int = Field(default=0, ge=0)
    uncited_claims_count: int = Field(default=0, ge=0)
    invalid_citation_ids: List[str] = Field(
        default_factory=list, description="Citation IDs cited by LLM but missing from context"
    )
    claim_results: List[ClaimVerificationResult] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list, description="Diagnostic validation warnings")
    should_regenerate: bool = Field(
        default=False, description="True if evidence is severely insufficient or hallucination detected"
    )


class PDFViewportCoords(BaseModel):
    """
    Converted bounding box coordinates mapped to PDF.js viewport display.
    """
    page_number: int = Field(description="1-indexed target PDF page number")
    x_pct: float = Field(description="Left percentage relative to page width (0.0 - 100.0)")
    y_pct: float = Field(description="Top percentage relative to page height (0.0 - 100.0)")
    width_pct: float = Field(description="Width percentage relative to page width")
    height_pct: float = Field(description="Height percentage relative to page height")
    viewport_x0: float = Field(description="Calculated pixel X0 in viewport")
    viewport_y0: float = Field(description="Calculated pixel Y0 in viewport")
    viewport_x1: float = Field(description="Calculated pixel X1 in viewport")
    viewport_y1: float = Field(description="Calculated pixel Y1 in viewport")
    bbox_pdf_points: Dict[str, float] = Field(description="Original PDF point bounding box")


class EvidenceMappingRequest(BaseModel):
    """
    Request model for converting citation to PDF.js viewport coordinates.
    """
    citation_id: str
    chunk_id: Optional[uuid.UUID] = None
    bbox: Optional[Dict[str, float]] = None
    page_number: Optional[int] = 1
    viewport_width: float = Field(default=800.0, gt=0)
    viewport_height: float = Field(default=1100.0, gt=0)
    zoom_scale: float = Field(default=1.0, gt=0)
    rotation_degrees: int = Field(default=0, description="Rotation in degrees (0, 90, 180, 270)")


class EvidenceMappingResponse(BaseModel):
    """
    Response model providing viewport bounding box overlay and PDF asset location.
    """
    citation_id: str
    document_id: uuid.UUID
    document_title: str
    page_number: int
    pdf_asset_url: str = Field(description="Endpoint URL to fetch source PDF binary asset")
    viewport_coords: PDFViewportCoords
    snippet_text: str
    doi: Optional[str] = None
