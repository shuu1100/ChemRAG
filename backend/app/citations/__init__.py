"""
ChemRAG — Citations & Provenance Package
=========================================
Exports Citation Engine, Citation Validator, and PDF.js Evidence Mapper.
"""
from backend.app.citations.engine import CitationEngine
from backend.app.citations.evidence_mapper import EvidenceMapper
from backend.app.citations.models import (
    CitationMetadata,
    CitationValidationResult,
    ClaimVerificationResult,
    EvidenceMappingRequest,
    EvidenceMappingResponse,
    PDFViewportCoords,
)
from backend.app.citations.validator import CitationValidator

__all__ = [
    "CitationEngine",
    "CitationValidator",
    "EvidenceMapper",
    "CitationMetadata",
    "CitationValidationResult",
    "ClaimVerificationResult",
    "EvidenceMappingRequest",
    "EvidenceMappingResponse",
    "PDFViewportCoords",
]
