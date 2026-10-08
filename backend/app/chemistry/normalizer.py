"""
ChemRAG — Chemical Entity Normalizer
=====================================
Provides text-level normalization for chemical entity names to support
resilient restricted chemical screening:
- Lowercase, strip whitespace
- Remove dashes, underscores, and common separators
- Expand common abbreviations
- Remove leetspeak obfuscation
- Normalize Unicode characters to ASCII
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

from backend.app.core.logging import get_logger

logger = get_logger(__name__)


# Common chemical abbreviation expansions
ABBREVIATION_MAP: dict[str, str] = {
    "gb": "sarin",
    "gd": "soman",
    "ga": "tabun",
    "vx": "vx nerve agent",
    "gs": "novichok",
    "hd": "sulfur mustard",
    "hn": "nitrogen mustard",
    "cw": "chemical weapon",
    "cwa": "chemical warfare agent",
    "rdx": "rdx cyclotrimethylenetrinitramine",
    "hmx": "hmx cyclotetramethylenetetranitramine",
    "petn": "petn pentaerythritol tetranitrate",
    "tatp": "tatp triacetone triperoxide",
    "anfo": "ammonium nitrate fuel oil",
    "meth": "methamphetamine",
    "thc": "delta-9-tetrahydrocannabinol",
}

# Leetspeak / obfuscation substitution map
LEET_MAP: dict[str, str] = {
    "0": "o",
    "1": "l",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
    "@": "a",
    "$": "s",
    "!": "i",
    "|": "i",
}


class ChemicalEntityNormalizer:
    """
    Text-level chemical entity normalizer for restricted screening.
    Converts adversarial or variant representations into a canonical
    lowercase ASCII form for reliable matching.
    """

    def normalize(self, text: str) -> str:
        """
        Normalize a chemical name or identifier string.
        Returns a canonical lowercase ASCII string.
        """
        if not text:
            return ""

        # 1. Unicode normalization (NFKD) to decompose accented chars
        text = unicodedata.normalize("NFKD", text)
        text = text.encode("ascii", errors="ignore").decode("ascii")

        # 2. Lowercase
        text = text.lower()

        # 3. Apply leetspeak substitutions
        for leet, normal in LEET_MAP.items():
            text = text.replace(leet, normal)

        # 4. Remove repeated punctuation and separators
        text = re.sub(r"[\-_\.]{2,}", " ", text)  # triple dashes → space
        text = re.sub(r"[^\w\s]", " ", text)        # non-alphanumeric → space

        # 5. Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # 6. Expand abbreviations
        tokens = text.split()
        expanded = []
        for token in tokens:
            expanded.append(ABBREVIATION_MAP.get(token, token))
        text = " ".join(expanded)

        return text

    def normalize_smiles(self, smiles: str) -> str:
        """
        Basic SMILES normalization (strip whitespace, keep canonical form as-is).
        Full canonicalization requires RDKit; this is the fallback.
        """
        if not smiles:
            return ""
        return smiles.strip()

    def normalize_cas(self, cas: str) -> str:
        """
        Normalize a CAS number to the standard hyphenated format (XXXXXXX-YY-Z).
        Strips all non-digit characters then re-inserts hyphens.
        """
        if not cas:
            return ""
        digits = re.sub(r"[^\d]", "", cas)
        if len(digits) < 5:
            return cas.strip()
        # Standard: last digit is checksum, 2 before that, rest is registry
        return f"{digits[:-3]}-{digits[-3:-1]}-{digits[-1]}"

    def fuzzy_match_score(self, normalized_query: str, normalized_target: str) -> float:
        """
        Simple token overlap score for fuzzy matching (0.0–1.0).
        Higher = more overlap between query and target tokens.
        """
        q_tokens = set(normalized_query.split())
        t_tokens = set(normalized_target.split())
        if not q_tokens or not t_tokens:
            return 0.0
        intersection = q_tokens & t_tokens
        union = q_tokens | t_tokens
        return len(intersection) / len(union)

    def contains_restricted_term(
        self, text: str, restricted_terms: list[str], threshold: float = 0.5
    ) -> tuple[bool, Optional[str]]:
        """
        Check if normalized text contains any restricted term.
        Returns (matched: bool, matched_term: Optional[str]).
        """
        normalized = self.normalize(text)
        for term in restricted_terms:
            normalized_term = self.normalize(term)
            # Exact substring match after normalization
            if normalized_term in normalized:
                return True, term
            # Fuzzy token overlap for multi-word terms
            if len(normalized_term.split()) > 1:
                score = self.fuzzy_match_score(normalized, normalized_term)
                if score >= threshold:
                    return True, term
        return False, None
