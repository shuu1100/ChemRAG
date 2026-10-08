"""
ChemRAG — PDF.js Evidence Mapper
================================
Fulfills Prompt 13.3:
- Converts PDF point coordinates (top-left/bottom-left origin) to web DOM viewport pixel coordinates.
- Calculates percentage-based normalized coordinates (x_pct, y_pct, width_pct, height_pct) for responsive overlays.
- Supports viewport scaling (zoom), page rotation (0, 90, 180, 270 degrees), and multi-page citation highlights.
- Binds citation request to PDF binary asset retrieval URL for frontend PDF.js rendering.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
import uuid

from backend.app.citations.models import (
    CitationMetadata,
    EvidenceMappingRequest,
    EvidenceMappingResponse,
    PDFViewportCoords,
)

logger = logging.getLogger(__name__)

# Standard PDF page dimensions in points (72 points = 1 inch)
DEFAULT_PDF_WIDTH_POINTS = 612.0   # Letter / A4 width approx
DEFAULT_PDF_HEIGHT_POINTS = 792.0  # Letter / A4 height approx


class EvidenceMapper:
    """
    Handles coordinate transformations and evidence location mapping for PDF.js overlays.
    """

    def calculate_viewport_coords(
        self,
        bbox: Dict[str, float],
        viewport_width: float = 800.0,
        viewport_height: float = 1100.0,
        zoom_scale: float = 1.0,
        rotation_degrees: int = 0,
        page_width_pts: float = DEFAULT_PDF_WIDTH_POINTS,
        page_height_pts: float = DEFAULT_PDF_HEIGHT_POINTS,
    ) -> PDFViewportCoords:
        """
        Converts bounding box in PDF points (x0, y0, x1, y1) into viewport pixel coordinates
        and relative percentage coordinates, accounting for zoom scale and page rotation.
        """
        x0 = float(bbox.get("x0", 0.0))
        y0 = float(bbox.get("y0", 0.0))
        x1 = float(bbox.get("x1", page_width_pts * 0.5))
        y1 = float(bbox.get("y1", page_height_pts * 0.1))

        # Clamp bounding box values
        x0 = max(0.0, min(page_width_pts, x0))
        x1 = max(x0, min(page_width_pts, x1))
        y0 = max(0.0, min(page_height_pts, y0))
        y1 = max(y0, min(page_height_pts, y1))

        # Handle page rotation (0, 90, 180, 270)
        rot = rotation_degrees % 360
        if rot == 90:
            rx0, ry0 = page_height_pts - y1, x0
            rx1, ry1 = page_height_pts - y0, x1
            pw, ph = page_height_pts, page_width_pts
        elif rot == 180:
            rx0, ry0 = page_width_pts - x1, page_height_pts - y1
            rx1, ry1 = page_width_pts - x0, page_height_pts - y0
            pw, ph = page_width_pts, page_height_pts
        elif rot == 270:
            rx0, ry0 = y0, page_width_pts - x1
            rx1, ry1 = y1, page_width_pts - x0
            pw, ph = page_height_pts, page_width_pts
        else:
            rx0, ry0, rx1, ry1 = x0, y0, x1, y1
            pw, ph = page_width_pts, page_height_pts

        # Calculate percentage coordinates relative to page dimensions
        x_pct = round((rx0 / pw) * 100.0, 3)
        y_pct = round((ry0 / ph) * 100.0, 3)
        width_pct = round(((rx1 - rx0) / pw) * 100.0, 3)
        height_pct = round(((ry1 - ry0) / ph) * 100.0, 3)

        # Scale to target viewport pixels
        scaled_w = viewport_width * zoom_scale
        scaled_h = viewport_height * zoom_scale

        vp_x0 = round((rx0 / pw) * scaled_w, 2)
        vp_y0 = round((ry0 / ph) * scaled_h, 2)
        vp_x1 = round((rx1 / pw) * scaled_w, 2)
        vp_y1 = round((ry1 / ph) * scaled_h, 2)

        return PDFViewportCoords(
            page_number=1,
            x_pct=x_pct,
            y_pct=y_pct,
            width_pct=width_pct,
            height_pct=height_pct,
            viewport_x0=vp_x0,
            viewport_y0=vp_y0,
            viewport_x1=vp_x1,
            viewport_y1=vp_y1,
            bbox_pdf_points={"x0": x0, "y0": y0, "x1": x1, "y1": y1},
        )

    def map_evidence(
        self,
        citation: CitationMetadata,
        req: EvidenceMappingRequest,
        api_base_url: str = "/api/v1",
    ) -> EvidenceMappingResponse:
        """
        Generate full evidence mapping response binding citation to PDF asset URL and viewport overlay.
        """
        page_num = citation.page_number or req.page_number or 1
        bbox_dict = citation.bbox or req.bbox or {"x0": 50.0, "y0": 100.0, "x1": 500.0, "y1": 200.0}

        vp_coords = self.calculate_viewport_coords(
            bbox=bbox_dict,
            viewport_width=req.viewport_width,
            viewport_height=req.viewport_height,
            zoom_scale=req.zoom_scale,
            rotation_degrees=req.rotation_degrees,
        )
        vp_coords.page_number = page_num

        pdf_asset_url = f"{api_base_url.rstrip('/')}/documents/{citation.document_id}/file"

        return EvidenceMappingResponse(
            citation_id=citation.citation_id,
            document_id=citation.document_id,
            document_title=citation.document_title,
            page_number=page_num,
            pdf_asset_url=pdf_asset_url,
            viewport_coords=vp_coords,
            snippet_text=citation.raw_text,
            doi=citation.doi,
        )
