"""
ChemRAG — Unified Scientific PDF Parsing Service
=================================================
Orchestrates PyMuPDF layout extraction, GROBID scholarly enrichment,
dedicated table extraction, and equation recognition into a single
traceable ParsedDocument.
"""
from __future__ import annotations

from typing import Optional

import pymupdf

from backend.app.core.logging import get_logger
from backend.app.parsing.equation_extractor import EquationExtractor
from backend.app.parsing.grobid_client import GrobidClient, GrobidResult
from backend.app.parsing.layout_extractor import (
    CorruptedPDFError,
    EmptyPDFError,
    LayoutExtractor,
    PDFParsingError,
)
from backend.app.parsing.models import ParsedDocument, ParsedPage
from backend.app.parsing.table_extractor import TableExtractor

logger = get_logger(__name__)


class ScientificPDFParser:
    """
    High-level orchestrator for parsing scientific chemistry PDFs.
    """

    def __init__(
        self,
        layout_extractor: Optional[LayoutExtractor] = None,
        table_extractor: Optional[TableExtractor] = None,
        equation_extractor: Optional[EquationExtractor] = None,
        grobid_client: Optional[GrobidClient] = None,
    ) -> None:
        self.layout_extractor = layout_extractor or LayoutExtractor()
        self.table_extractor = table_extractor or TableExtractor()
        self.equation_extractor = equation_extractor or EquationExtractor()
        self.grobid_client = grobid_client or GrobidClient()

    async def parse(
        self,
        pdf_bytes: bytes,
        filename: str = "document.pdf",
        enable_grobid: bool = True,
    ) -> ParsedDocument:
        """
        Parses PDF into a unified ParsedDocument with spatial coordinates,
        tables, equations, and scholarly metadata.
        """
        if not pdf_bytes:
            raise EmptyPDFError(f"Cannot parse empty PDF bytes for '{filename}'.")

        logger.info("Starting scientific PDF parsing", filename=filename, size_bytes=len(pdf_bytes))

        # 1. PyMuPDF Layout Extraction (Spatial Ground Truth)
        parsed_doc = self.layout_extractor.extract(pdf_bytes, filename=filename)

        # 2. Extract Tables & Equations page-by-page using PyMuPDF doc handle
        try:
            doc_handle = pymupdf.open(stream=pdf_bytes, filetype="pdf")
            for page_idx, parsed_page in enumerate(parsed_doc.pages):
                pymupdf_page = doc_handle[page_idx]

                # Extract Tables
                page_tables = self.table_extractor.extract_from_pymupdf_page(
                    pymupdf_page,
                    page_number=parsed_page.page_number,
                    cached_page_text=parsed_page.raw_text,
                )
                parsed_page.tables.extend(page_tables)
                parsed_doc.tables.extend(page_tables)

                # Extract Equations
                page_equations = self.equation_extractor.extract_from_page(parsed_page)
                parsed_page.equations.extend(page_equations)
                parsed_doc.equations.extend(page_equations)

            doc_handle.close()
        except Exception as exc:
            logger.warning("Error during table/equation extraction pass", error=str(exc))

        # 3. GROBID Scholarly Enrichment (Metadata, Sections, Citations)
        if enable_grobid:
            try:
                grobid_res: GrobidResult = await self.grobid_client.parse_pdf(pdf_bytes, filename=filename)
                if grobid_res.is_available:
                    if grobid_res.title and not parsed_doc.title:
                        parsed_doc.title = grobid_res.title
                    if grobid_res.authors and not parsed_doc.authors:
                        parsed_doc.authors = grobid_res.authors
                    if grobid_res.doi:
                        parsed_doc.doi = grobid_res.doi
                    if grobid_res.abstract:
                        parsed_doc.abstract = grobid_res.abstract
                    if grobid_res.sections:
                        parsed_doc.sections = grobid_res.sections
                    if grobid_res.references:
                        parsed_doc.references = grobid_res.references
                    logger.info(
                        "GROBID enrichment applied",
                        sections_count=len(grobid_res.sections),
                        refs_count=len(grobid_res.references),
                    )
            except Exception as exc:
                logger.info("GROBID enrichment skipped due to exception", error=str(exc))

        logger.info(
            "Scientific PDF parsing completed",
            filename=filename,
            pages=parsed_doc.page_count,
            tables=len(parsed_doc.tables),
            equations=len(parsed_doc.equations),
        )
        return parsed_doc
