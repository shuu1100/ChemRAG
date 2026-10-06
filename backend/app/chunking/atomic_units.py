"""
ChemRAG — Atomic Chemical & Procedural Unit Protection
======================================================
Guarantees that chunk boundaries NEVER arbitrarily split:
- SMILES representations
- InChI and InChIKeys
- Chemical formulas and complex coordination compounds
- Mathematical and LaTeX equations
- Table rows
- Safety hazard warnings (H/P statements, Signal Words)
- Procedural SOP steps
"""
from __future__ import annotations

import re
from typing import List, Tuple

# Protected patterns
ATOMIC_PATTERNS = [
    # InChI strings
    re.compile(r"InChI=1S?/[A-Za-z0-9\(\)\+\-\,\.\/\;\:\?\#]+"),
    # InChIKey
    re.compile(r"\b[A-Z]{14}-[A-Z]{10}-[A-Z\d]\b"),
    # Common SMILES patterns (chains with brackets/branches)
    re.compile(r"\b[A-Z][A-Za-z0-9@\+\-\#\$\:\/\\\[\]\(\)\=]{5,}\b"),
    # LaTeX display and inline equations
    re.compile(r"\$\$.*?\$\$", re.DOTALL),
    re.compile(r"\\\[.*?\\\]", re.DOTALL),
    re.compile(r"\\begin\{equation\}.*?\\end\{equation\}", re.DOTALL),
    # Safety warnings (GHS, H/P statements)
    re.compile(r"\b(?:DANGER|WARNING|CAUTION)\b[:\s].*?(?:\.|\n|$)", re.IGNORECASE),
    re.compile(r"\b[HP]\d{3}\b[:\s].*?(?:\.|\n|$)"),
    # Table rows formatted as 'Row N: ...'
    re.compile(r"^Row\s+\d+:.*?$", re.MULTILINE),
    # Numbered SOP procedural steps e.g. "Step 1.2: ..." or "3.4 Transfer 50 mL..."
    re.compile(r"^(?:Step\s+)?\d+(?:\.\d+)*[:\.]\s+.*?$", re.MULTILINE),
]


class AtomicUnitGuard:
    """
    Prevents text chunkers from splitting indivisible scientific and procedural tokens.
    """

    def find_atomic_spans(self, text: str) -> List[Tuple[int, int]]:
        """
        Locates all indivisible ranges [start_idx, end_idx) in text.
        """
        spans: List[Tuple[int, int]] = []
        if not text:
            return spans

        for pattern in ATOMIC_PATTERNS:
            for match in pattern.finditer(text):
                spans.append((match.start(), match.end()))

        # Merge overlapping or contiguous spans
        if not spans:
            return []

        spans.sort(key=lambda s: s[0])
        merged: List[Tuple[int, int]] = [spans[0]]

        for current in spans[1:]:
            prev_start, prev_end = merged[-1]
            if current[0] <= prev_end:
                merged[-1] = (prev_start, max(prev_end, current[1]))
            else:
                merged.append(current)

        return merged

    def is_safe_split_point(self, text: str, index: int, atomic_spans: List[Tuple[int, int]]) -> bool:
        """
        Returns True if `index` does not lie inside any atomic span.
        """
        for start, end in atomic_spans:
            if start < index < end:
                return False
        return True

    def adjust_split_to_safe_boundary(
        self,
        text: str,
        desired_idx: int,
        atomic_spans: List[Tuple[int, int]],
    ) -> int:
        """
        If `desired_idx` falls inside an atomic unit, shifts boundary to either
        the beginning or end of the atomic unit (whichever keeps chunk size closer).
        """
        for start, end in atomic_spans:
            if start < desired_idx < end:
                # If closer to end and within reasonable distance, push past end
                if (desired_idx - start) > (end - desired_idx):
                    return end
                else:
                    return start
        return desired_idx
