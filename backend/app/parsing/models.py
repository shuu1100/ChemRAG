"""
ChemRAG — Structured Intermediate Representation for Scientific PDF Parsing
=============================================================================
Preserves spatial coordinates (BoundingBox), font metadata, reading order,
tables with header context, and equations with LaTeX and confidence.
Never flattens immediately into plain text.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BoundingBox:
    """Spatially traceable rectangular coordinates [x0, y0, x1, y1] in points."""
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return max(0.0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0.0, self.y1 - self.y0)

    @property
    def area(self) -> float:
        return self.width * self.height

    def overlaps(self, other: "BoundingBox") -> bool:
        """Check if this bounding box overlaps another."""
        return not (
            self.x1 <= other.x0
            or self.x0 >= other.x1
            or self.y1 <= other.y0
            or self.y0 >= other.y1
        )

    def contains(self, other: "BoundingBox") -> bool:
        """Check if this bounding box completely encloses another."""
        return (
            self.x0 <= other.x0
            and self.y0 <= other.y0
            and self.x1 >= other.x1
            and self.y1 >= other.y1
        )

    def to_dict(self) -> Dict[str, float]:
        return {"x0": round(self.x0, 2), "y0": round(self.y0, 2), "x1": round(self.x1, 2), "y1": round(self.y1, 2)}


@dataclass
class ParsedSpan:
    """Individual text span with typography and precise bounding box."""
    text: str
    bbox: BoundingBox
    font_name: str = ""
    font_size: float = 0.0
    is_bold: bool = False
    is_italic: bool = False
    color: int = 0


@dataclass
class ParsedLine:
    """Line containing multiple text spans."""
    spans: List[ParsedSpan] = field(default_factory=list)
    bbox: Optional[BoundingBox] = None
    text: str = ""


@dataclass
class ParsedBlock:
    """Structural text block containing lines."""
    block_id: int
    block_type: str = "text"  # text, heading, list_item, caption, header, footer
    lines: List[ParsedLine] = field(default_factory=list)
    bbox: Optional[BoundingBox] = None
    text: str = ""


@dataclass
class ParsedImage:
    """Embedded raster image or diagram extracted from page."""
    image_index: int
    bbox: BoundingBox
    width: int
    height: int
    image_bytes: Optional[bytes] = None
    format: str = "png"
    caption: Optional[str] = None


@dataclass
class ParsedTable:
    """
    Dedicated structured table representation.
    Preserves column headers, row headers, units, footnotes, and retrieval-friendly contextual text.
    """
    table_index: int
    caption: str
    bbox: Optional[BoundingBox]
    page_number: int
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    units: Dict[str, str] = field(default_factory=dict)
    footnotes: List[str] = field(default_factory=list)
    raw_html: str = ""
    retrieval_text: str = ""  # Rows with full table and column header context

    def generate_retrieval_text(self) -> str:
        """
        Produces context-rich text representation where every cell value retains its column header
        and table title so chunks retrieved by dense/sparse search have complete context.
        """
        lines = []
        if self.caption:
            cap_clean = self.caption.strip()
            if cap_clean.lower().startswith("table"):
                lines.append(f"[{cap_clean}]")
            else:
                lines.append(f"[Table {self.table_index}: {cap_clean}]")
        else:
            lines.append(f"[Table {self.table_index}]")

        for row_idx, row in enumerate(self.rows):
            row_parts = []
            for col_idx, cell in enumerate(row):
                header = self.headers[col_idx] if col_idx < len(self.headers) else f"Col {col_idx + 1}"
                unit = (
                    f" ({self.units[header]})"
                    if (header in self.units and f"({self.units[header]})" not in header)
                    else ""
                )
                row_parts.append(f"{header}{unit}: {cell}")
            lines.append(f"Row {row_idx + 1}: " + " | ".join(row_parts))


        if self.footnotes:
            lines.append("Notes: " + " ; ".join(self.footnotes))

        self.retrieval_text = "\n".join(lines)
        return self.retrieval_text


@dataclass
class ParsedEquation:
    """
    Equation or mathematical expression.
    Preserves LaTeX, normalized form, bounding box, and confidence.
    """
    equation_index: int
    raw_text: str
    latex: str
    bbox: Optional[BoundingBox]
    page_number: int
    confidence: float = 1.0
    is_inline: bool = False


@dataclass
class ParsedSection:
    """Scholarly section identified via layout or GROBID TEI XML."""
    title: str
    level: int = 1
    text: str = ""
    page_start: int = 1
    page_end: int = 1
    subsections: List["ParsedSection"] = field(default_factory=list)


@dataclass
class ParsedReference:
    """Bibliographic citation reference."""
    ref_index: int
    raw_text: str
    title: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    doi: Optional[str] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    pages: Optional[str] = None


@dataclass
class ParsedPage:
    """Parsed single page containing blocks, images, tables, equations, and dimensions."""
    page_number: int
    width: float
    height: float
    blocks: List[ParsedBlock] = field(default_factory=list)
    images: List[ParsedImage] = field(default_factory=list)
    tables: List[ParsedTable] = field(default_factory=list)
    equations: List[ParsedEquation] = field(default_factory=list)
    raw_text: str = ""


@dataclass
class ParsedDocument:
    """Root structured document intermediate representation."""
    doc_id: Optional[str]
    filename: str
    page_count: int
    pages: List[ParsedPage] = field(default_factory=list)
    title: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    abstract: Optional[str] = None
    doi: Optional[str] = None
    sections: List[ParsedSection] = field(default_factory=list)
    references: List[ParsedReference] = field(default_factory=list)
    tables: List[ParsedTable] = field(default_factory=list)
    equations: List[ParsedEquation] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
