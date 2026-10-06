"""
ChemRAG — Dedicated Scientific Table Extraction Pipeline
=========================================================
Extracts tables preserving title, caption, column headers, row headers,
units, footnotes, rows, cells, coordinates, page number, and bounding box.
Produces both structured JSON and retrieval-friendly contextual text where
every row retains full table title and column header context.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import pymupdf

from backend.app.core.logging import get_logger
from backend.app.parsing.models import BoundingBox, ParsedPage, ParsedTable

logger = get_logger(__name__)

# Pattern to capture units in column headers, e.g. "Yield (%)", "Temperature (°C)", "Retention Time (min)"
UNIT_PATTERN = re.compile(r"\(([^)]+)\)|\[([^\]]+)\]")
TABLE_CAPTION_PATTERN = re.compile(r"^(?:Table|TABLE)\s+(?:\d+|[A-Z]\d*|\b[iIvVxX]+\b)[:\.\s]?(.*)", re.IGNORECASE)
FOOTNOTE_PATTERN = re.compile(r"^(?:[\*\†\‡\§]|\b[a-z]\b|\b\d+\b)\s+(.+)")


class TableExtractor:
    """
    Extracts tabular data from PDF pages using PyMuPDF table finder with heuristic fallback.
    """

    def extract_from_pymupdf_page(
        self,
        page: pymupdf.Page,
        page_number: int,
        cached_page_text: str = "",
    ) -> List[ParsedTable]:
        """
        Extract tables from PyMuPDF page using native table detection.
        """
        tables: List[ParsedTable] = []

        try:
            tab_finder = page.find_tables()
            if tab_finder and tab_finder.tables:
                for idx, t in enumerate(tab_finder.tables):
                    bbox = BoundingBox(
                        x0=float(t.bbox[0]),
                        y0=float(t.bbox[1]),
                        x1=float(t.bbox[2]),
                        y1=float(t.bbox[3]),
                    )

                    extracted = t.extract()
                    if not extracted or len(extracted) < 1:
                        continue

                    # First row or headers
                    raw_headers = [str(c or "").strip() for c in extracted[0]]
                    raw_rows = []
                    for r in extracted[1:]:
                        clean_row = [str(c or "").strip() for c in r]
                        # Don't add completely empty rows
                        if any(clean_row):
                            raw_rows.append(clean_row)

                    # Extract units from headers
                    units = self._extract_units(raw_headers)

                    # Search for caption in proximity
                    caption = self._find_caption_near_bbox(page, bbox)

                    # Search for footnotes below table
                    footnotes = self._find_footnotes_near_bbox(page, bbox)

                    table = ParsedTable(
                        table_index=idx + 1,
                        caption=caption or f"Table {idx + 1}",
                        bbox=bbox,
                        page_number=page_number,
                        headers=raw_headers,
                        rows=raw_rows,
                        units=units,
                        footnotes=footnotes,
                        raw_html=self._to_html(caption, raw_headers, raw_rows, footnotes),
                    )
                    table.generate_retrieval_text()
                    tables.append(table)

        except Exception as exc:
            logger.warning("PyMuPDF find_tables encountered error, trying fallback", page=page_number, error=str(exc))

        # If no tables found by find_tables, check heuristic table detection
        if not tables and cached_page_text:
            heuristic_tables = self.extract_from_text(cached_page_text, page_number)
            tables.extend(heuristic_tables)

        return tables

    def extract_from_text(self, text: str, page_number: int) -> List[ParsedTable]:
        """
        Heuristic fallback to extract tables from text blocks (e.g. Markdown or aligned columns).
        """
        tables: List[ParsedTable] = []
        lines = [line.rstrip() for line in text.split("\n")]
        i = 0

        while i < len(lines):
            line = lines[i].strip()
            match = TABLE_CAPTION_PATTERN.match(line)
            if match:
                caption = line
                i += 1
                headers: List[str] = []
                rows: List[List[str]] = []
                footnotes: List[str] = []

                # Look for table rows (delimiter or tab/pipe separated)
                while i < len(lines) and lines[i].strip():
                    current = lines[i].strip()
                    # Check for delimiter line e.g. |---|---|
                    if set(current).issubset({"-", "|", ":", "+", " "}):
                        i += 1
                        continue

                    # Split by pipe or tabs or multiple spaces
                    if "|" in current:
                        cells = [c.strip() for c in current.split("|") if c.strip()]
                    elif "\t" in current:
                        cells = [c.strip() for c in current.split("\t") if c.strip()]
                    else:
                        cells = [c.strip() for c in re.split(r"\s{2,}", current) if c.strip()]

                    if len(cells) >= 2:
                        if not headers:
                            headers = cells
                        else:
                            rows.append(cells)
                    elif FOOTNOTE_PATTERN.match(current):
                        footnotes.append(current)
                    i += 1

                if headers and rows:
                    units = self._extract_units(headers)
                    table = ParsedTable(
                        table_index=len(tables) + 1,
                        caption=caption,
                        bbox=None,
                        page_number=page_number,
                        headers=headers,
                        rows=rows,
                        units=units,
                        footnotes=footnotes,
                        raw_html=self._to_html(caption, headers, rows, footnotes),
                    )
                    table.generate_retrieval_text()
                    tables.append(table)
            else:
                i += 1

        return tables

    def _extract_units(self, headers: List[str]) -> Dict[str, str]:
        """Extract units from column headers like 'Yield (%)' -> {'Yield (%)': '%'."""
        units: Dict[str, str] = {}
        for h in headers:
            match = UNIT_PATTERN.search(h)
            if match:
                unit = match.group(1) or match.group(2)
                units[h] = unit.strip()
        return units

    def _find_caption_near_bbox(self, page: pymupdf.Page, table_bbox: BoundingBox) -> str:
        """Search for a caption block located directly above the table."""
        text_dict = page.get_text("dict")
        best_caption = ""
        min_distance = 100.0

        for b in text_dict.get("blocks", []):
            if b.get("type", 0) == 0:  # text
                by0 = float(b["bbox"][1])
                by1 = float(b["bbox"][3])
                # Check blocks above the table within 60 points
                if by1 <= table_bbox.y0 and (table_bbox.y0 - by1) < min_distance:
                    block_text = "".join(
                        span.get("text", "") for l in b.get("lines", []) for span in l.get("spans", [])
                    ).strip()
                    if TABLE_CAPTION_PATTERN.match(block_text):
                        best_caption = block_text
                        min_distance = table_bbox.y0 - by1

        return best_caption

    def _find_footnotes_near_bbox(self, page: pymupdf.Page, table_bbox: BoundingBox) -> List[str]:
        """Search for footnotes immediately below the table."""
        text_dict = page.get_text("dict")
        footnotes: List[str] = []

        for b in text_dict.get("blocks", []):
            if b.get("type", 0) == 0:  # text
                by0 = float(b["bbox"][1])
                # Check blocks below table within 50 points
                if by0 >= table_bbox.y1 and (by0 - table_bbox.y1) < 50.0:
                    block_text = "".join(
                        span.get("text", "") for l in b.get("lines", []) for span in l.get("spans", [])
                    ).strip()
                    if FOOTNOTE_PATTERN.match(block_text) or block_text.startswith("Note"):
                        footnotes.append(block_text)

        return footnotes

    def _to_html(self, caption: str, headers: List[str], rows: List[List[str]], footnotes: List[str]) -> str:
        """Render table to standard HTML."""
        html_parts = ["<table>"]
        if caption:
            html_parts.append(f"<caption>{caption}</caption>")
        if headers:
            html_parts.append("<thead><tr>")
            for h in headers:
                html_parts.append(f"<th>{h}</th>")
            html_parts.append("</tr></thead>")
        if rows:
            html_parts.append("<tbody>")
            for row in rows:
                html_parts.append("<tr>")
                for cell in row:
                    html_parts.append(f"<td>{cell}</td>")
                html_parts.append("</tr>")
            html_parts.append("</tbody>")
        if footnotes:
            html_parts.append("<tfoot><tr>")
            html_parts.append(f"<td colspan='{len(headers)}'>{'<br/>'.join(footnotes)}</td>")
            html_parts.append("</tr></tfoot>")
        html_parts.append("</table>")
        return "".join(html_parts)
