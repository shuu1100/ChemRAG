"""
ChemRAG — Scientific PDF Layout Extractor (PyMuPDF)
===================================================
Extracts pages, text blocks, lines, spans, bounding box coordinates,
font metadata, embedded images, page dimensions, and reading order.
Never flattens immediately into plain text.
Raises explicit exceptions for parsing failures.
"""
from __future__ import annotations

import io
from typing import Any, Dict, List, Optional, Tuple

import pymupdf

from backend.app.core.logging import get_logger
from backend.app.parsing.models import (
    BoundingBox,
    ParsedBlock,
    ParsedDocument,
    ParsedImage,
    ParsedLine,
    ParsedPage,
    ParsedSpan,
)

logger = get_logger(__name__)


class PDFParsingError(Exception):
    """Base exception for PDF parsing failures."""
    pass


class CorruptedPDFError(PDFParsingError):
    """Raised when a PDF file is malformed or corrupted."""
    pass


class EmptyPDFError(PDFParsingError):
    """Raised when a PDF file contains 0 pages or no extractable content."""
    pass


class LayoutExtractor:
    """
    Extracts spatial layout, typography, and embedded assets using PyMuPDF.
    """

    def extract(self, pdf_bytes: bytes, filename: str = "document.pdf") -> ParsedDocument:
        """
        Parses PDF bytes into a structured intermediate representation.
        """
        if not pdf_bytes:
            raise EmptyPDFError(f"Cannot parse empty PDF bytes for '{filename}'.")

        try:
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        except Exception as exc:
            raise CorruptedPDFError(f"Failed to open PDF document '{filename}': {exc}") from exc

        try:
            page_count = len(doc)
            if page_count == 0:
                raise EmptyPDFError(f"PDF document '{filename}' has 0 pages.")

            parsed_pages: List[ParsedPage] = []

            for page_idx in range(page_count):
                page = doc[page_idx]
                parsed_page = self._extract_page(page, page_idx + 1)
                parsed_pages.append(parsed_page)

            # Metadata dictionary
            meta = {
                "format": doc.metadata.get("format", "PDF"),
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "creator": doc.metadata.get("creator", ""),
                "producer": doc.metadata.get("producer", ""),
                "creation_date": doc.metadata.get("creationDate", ""),
            }

            return ParsedDocument(
                doc_id=None,
                filename=filename,
                page_count=page_count,
                pages=parsed_pages,
                title=meta.get("title") or None,
                authors=[meta["author"]] if meta.get("author") else [],
                metadata=meta,
            )

        finally:
            doc.close()

    def _extract_page(self, page: pymupdf.Page, page_number: int) -> ParsedPage:
        rect = page.rect
        width = float(rect.width)
        height = float(rect.height)

        text_dict = page.get_text("dict")
        raw_blocks = text_dict.get("blocks", [])

        # Separate text blocks and image blocks
        parsed_blocks: List[ParsedBlock] = []
        parsed_images: List[ParsedImage] = []
        block_counter = 0

        for b in raw_blocks:
            b_type = b.get("type", 0)  # 0 = text, 1 = image
            bbox = BoundingBox(
                x0=float(b["bbox"][0]),
                y0=float(b["bbox"][1]),
                x1=float(b["bbox"][2]),
                y1=float(b["bbox"][3]),
            )

            if b_type == 0:
                # Text block
                lines: List[ParsedLine] = []
                full_block_text = []

                for l in b.get("lines", []):
                    line_spans: List[ParsedSpan] = []
                    line_text_parts = []
                    line_bbox = BoundingBox(
                        x0=float(l["bbox"][0]),
                        y0=float(l["bbox"][1]),
                        x1=float(l["bbox"][2]),
                        y1=float(l["bbox"][3]),
                    )

                    for s in l.get("spans", []):
                        span_text = s.get("text", "")
                        if not span_text:
                            continue

                        span_flags = s.get("flags", 0)
                        # flags: 2=italic, 16=bold (or 2**4)
                        is_bold = bool(span_flags & (1 << 4)) or ("bold" in s.get("font", "").lower())
                        is_italic = bool(span_flags & (1 << 1)) or ("italic" in s.get("font", "").lower())

                        span_bbox = BoundingBox(
                            x0=float(s["bbox"][0]),
                            y0=float(s["bbox"][1]),
                            x1=float(s["bbox"][2]),
                            y1=float(s["bbox"][3]),
                        )

                        parsed_span = ParsedSpan(
                            text=span_text,
                            bbox=span_bbox,
                            font_name=s.get("font", ""),
                            font_size=float(s.get("size", 0.0)),
                            is_bold=is_bold,
                            is_italic=is_italic,
                            color=int(s.get("color", 0)),
                        )
                        line_spans.append(parsed_span)
                        line_text_parts.append(span_text)

                    line_str = " ".join(line_text_parts).strip()
                    if line_spans:
                        lines.append(ParsedLine(spans=line_spans, bbox=line_bbox, text=line_str))
                        full_block_text.append(line_str)

                block_str = "\n".join(full_block_text).strip()
                if lines:
                    parsed_block = ParsedBlock(
                        block_id=block_counter,
                        block_type="text",
                        lines=lines,
                        bbox=bbox,
                        text=block_str,
                    )
                    parsed_blocks.append(parsed_block)
                    block_counter += 1

            elif b_type == 1:
                # Image block
                parsed_image = ParsedImage(
                    image_index=len(parsed_images),
                    bbox=bbox,
                    width=int(b.get("width", bbox.width)),
                    height=int(b.get("height", bbox.height)),
                    format=b.get("ext", "png"),
                )
                parsed_images.append(parsed_image)

        # Detect two-column layout and sort blocks in natural reading order
        sorted_blocks = self._sort_reading_order(parsed_blocks, width)

        raw_page_text = page.get_text()

        return ParsedPage(
            page_number=page_number,
            width=width,
            height=height,
            blocks=sorted_blocks,
            images=parsed_images,
            raw_text=raw_page_text,
        )

    def _sort_reading_order(self, blocks: List[ParsedBlock], page_width: float) -> List[ParsedBlock]:
        """
        Sort blocks into logical reading order, handling multi-column scientific layouts.
        """
        if len(blocks) <= 1:
            return blocks

        # Check if page exhibits a two-column distribution
        midpoint = page_width / 2.0
        left_blocks = []
        right_blocks = []
        spanning_blocks = []

        for b in blocks:
            if not b.bbox:
                spanning_blocks.append(b)
                continue
            # If block spans across middle significantly
            if b.bbox.x0 < (midpoint - 30) and b.bbox.x1 > (midpoint + 30):
                spanning_blocks.append(b)
            elif b.bbox.x1 <= (midpoint + 30):
                left_blocks.append(b)
            else:
                right_blocks.append(b)

        # If significant count in both columns, sort column by column
        if len(left_blocks) >= 2 and len(right_blocks) >= 2:
            left_blocks.sort(key=lambda b: (b.bbox.y0 if b.bbox else 0))
            right_blocks.sort(key=lambda b: (b.bbox.y0 if b.bbox else 0))
            spanning_blocks.sort(key=lambda b: (b.bbox.y0 if b.bbox else 0))

            # Combine: spanning top blocks, then left column, right column, spanning bottom blocks
            result: List[ParsedBlock] = []
            for b in spanning_blocks:
                if b.bbox and b.bbox.y0 < height_threshold(left_blocks, right_blocks):
                    result.append(b)
            result.extend(left_blocks)
            result.extend(right_blocks)
            for b in spanning_blocks:
                if b not in result:
                    result.append(b)
            return result

        # Default: sort purely top-to-bottom then left-to-right
        return sorted(blocks, key=lambda b: (b.bbox.y0 if b.bbox else 0, b.bbox.x0 if b.bbox else 0))


def height_threshold(left: List[ParsedBlock], right: List[ParsedBlock]) -> float:
    min_y = 9999.0
    for b in left + right:
        if b.bbox and b.bbox.y0 < min_y:
            min_y = b.bbox.y0
    return min_y
