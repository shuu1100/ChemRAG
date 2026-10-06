"""
ChemRAG — Scientific Equation & Mathematical Expression Extractor
==================================================================
Extracts display and inline scientific equations (chemical thermodynamics,
kinetics, quantum mechanics, rate laws, etc.).
Preserves raw equation, normalized LaTeX, page number, bounding box, and confidence.
Flags uncertainty so downstream agents never treat uncertain extractions as ground truth.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from backend.app.core.logging import get_logger
from backend.app.parsing.models import BoundingBox, ParsedBlock, ParsedEquation, ParsedPage

logger = get_logger(__name__)

# Common math/chemistry symbols mapped to LaTeX
MATH_SYMBOL_MAP = {
    "Δ": r"\Delta",
    "δ": r"\delta",
    "α": r"\alpha",
    "β": r"\beta",
    "γ": r"\gamma",
    "θ": r"\theta",
    "λ": r"\lambda",
    "μ": r"\mu",
    "π": r"\pi",
    "σ": r"\sigma",
    "ω": r"\omega",
    "±": r"\pm",
    "∓": r"\mp",
    "×": r"\times",
    "÷": r"\div",
    "·": r"\cdot",
    "°": r"^\circ",
    "≈": r"\approx",
    "≠": r"\neq",
    "≤": r"\leq",
    "≥": r"\geq",
    "→": r"\rightarrow",
    "⇌": r"\rightleftharpoons",
    "∑": r"\sum",
    "∏": r"\prod",
    "∫": r"\int",
    "∂": r"\partial",
    "∞": r"\infty",
    "Å": r"\text{\AA}",
}

# Regex to detect display equation blocks
EQUATION_NUMBER_PATTERN = re.compile(r"\((?:\d+|[A-Z]\d*|\b[iIvVxX]+\b)\)\s*$")
MATH_OPERATOR_PATTERN = re.compile(r"[=<>±≈≠≤≥⇌→]\s*")
LATEX_PATTERN = re.compile(r"(\$\$.*?\$\$|\$.*?\$|\\\[.*?\\\]|\\\(.*?\\\))")


class EquationExtractor:
    """
    Extracts mathematical and chemical equations from parsed pages.
    """

    def normalize_to_latex(self, text: str) -> str:
        """Converts raw mathematical/chemical text to standardized LaTeX."""
        clean = text.strip()
        # Strip existing delimiters if present
        clean = re.sub(r"^\$\$|\$\$$|^\\\[|\\\]$|^\$|\$$", "", clean).strip()

        # Replace Unicode symbols with LaTeX equivalents
        for char, latex in MATH_SYMBOL_MAP.items():
            clean = clean.replace(char, f" {latex} ")

        # Superscripts (e.g. ^2, ^-1, ^+)
        clean = re.sub(r"([A-Za-z0-9\)])\^([A-Za-z0-9\-+]+)", r"\1^{\2}", clean)
        # Subscripts (e.g. _2, _max, _eq)
        clean = re.sub(r"([A-Za-z0-9\)])_([A-Za-z0-9]+)", r"\1_{\2}", clean)

        # Collapse repeated spaces
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    def extract_from_page(self, page: ParsedPage) -> List[ParsedEquation]:
        """
        Scan blocks in a parsed page to extract equations with bounding boxes.
        """
        equations: List[ParsedEquation] = []

        for block in page.blocks:
            text = block.text.strip()
            if not text:
                continue

            eq_info = self._analyze_block(text, block.bbox, page.page_number)
            if eq_info:
                eq_info.equation_index = len(equations) + 1
                equations.append(eq_info)

        return equations

    def _analyze_block(
        self,
        text: str,
        bbox: Optional[BoundingBox],
        page_number: int,
    ) -> Optional[ParsedEquation]:
        """
        Analyze whether a text block contains a display or significant equation.
        """
        has_eq_num = bool(EQUATION_NUMBER_PATTERN.search(text))
        has_math_op = bool(MATH_OPERATOR_PATTERN.search(text))
        has_latex_markup = bool(LATEX_PATTERN.search(text))
        has_greek_or_symbol = any(sym in text for sym in MATH_SYMBOL_MAP.keys())

        # Check line length (equations are typically short, single lines or 1-2 lines)
        is_concise = len(text) < 250 and text.count("\n") <= 2

        # High confidence display equation
        if (has_eq_num and has_math_op) or has_latex_markup:
            confidence = 0.95
            latex = self.normalize_to_latex(text)
            return ParsedEquation(
                equation_index=0,
                raw_text=text,
                latex=latex,
                bbox=bbox,
                page_number=page_number,
                confidence=confidence,
                is_inline=False,
            )

        # Moderate confidence math expression
        if is_concise and has_math_op and has_greek_or_symbol:
            confidence = 0.75
            latex = self.normalize_to_latex(text)
            return ParsedEquation(
                equation_index=0,
                raw_text=text,
                latex=latex,
                bbox=bbox,
                page_number=page_number,
                confidence=confidence,
                is_inline=False,
            )

        return None
