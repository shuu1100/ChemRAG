"""
ChemRAG — Scientific PDF Parsing Package
"""
from __future__ import annotations

from backend.app.parsing.equation_extractor import EquationExtractor
from backend.app.parsing.grobid_client import GrobidClient, GrobidResult
from backend.app.parsing.layout_extractor import (
    CorruptedPDFError,
    EmptyPDFError,
    LayoutExtractor,
    PDFParsingError,
)
from backend.app.parsing.models import (
    BoundingBox,
    ParsedBlock,
    ParsedDocument,
    ParsedEquation,
    ParsedImage,
    ParsedLine,
    ParsedPage,
    ParsedReference,
    ParsedSection,
    ParsedSpan,
    ParsedTable,
)
from backend.app.parsing.service import ScientificPDFParser
from backend.app.parsing.table_extractor import TableExtractor

__all__ = [
    # Models
    "BoundingBox",
    "ParsedSpan",
    "ParsedLine",
    "ParsedBlock",
    "ParsedImage",
    "ParsedTable",
    "ParsedEquation",
    "ParsedSection",
    "ParsedReference",
    "ParsedPage",
    "ParsedDocument",
    # Components
    "LayoutExtractor",
    "TableExtractor",
    "EquationExtractor",
    "GrobidClient",
    "GrobidResult",
    "ScientificPDFParser",
    # Exceptions
    "PDFParsingError",
    "CorruptedPDFError",
    "EmptyPDFError",
]
