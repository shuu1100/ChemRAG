"""
ChemRAG — Document Classification Service
==========================================
Classifies chemical and scientific documents into target genres:
RESEARCH_PAPER, TEXTBOOK, EXPERIMENTAL_REPORT, SOP, SDS, TECHNICAL_REPORT, UNKNOWN.

Uses structural and text heuristics first, with pluggable support for ML/VLM classification.
Low confidence scores automatically fall back to the generic parser.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from backend.app.core.logging import get_logger
from backend.app.models.document import DocumentGenre

logger = get_logger(__name__)

# Recommended parsers per document genre
GENRE_PARSER_MAP: Dict[DocumentGenre, str] = {
    DocumentGenre.RESEARCH_PAPER: "grobid_parser",
    DocumentGenre.TEXTBOOK: "textbook_parser",
    DocumentGenre.EXPERIMENTAL_REPORT: "experimental_parser",
    DocumentGenre.SOP: "sop_parser",
    DocumentGenre.SDS: "sds_parser",
    DocumentGenre.TECHNICAL_REPORT: "tech_report_parser",
    DocumentGenre.UNKNOWN: "generic_parser",
}

# Weighted heuristic keywords
GENRE_SIGNALS: Dict[DocumentGenre, Dict[str, float]] = {
    DocumentGenre.SDS: {
        r"\bsafety\s+data\s+sheet\b": 3.0,
        r"\bmaterial\s+safety\s+data\s+sheet\b": 3.0,
        r"\bmsds\b": 2.0,
        r"\bghs\s+(classification|hazard)\b": 2.5,
        r"\bhazards?\s+identification\b": 2.0,
        r"\bfirst-?aid\s+measures\b": 2.0,
        r"\baccidental\s+release\s+measures\b": 2.0,
        r"\bexposure\s+controls\b": 2.0,
        r"\btoxicological\s+information\b": 2.0,
        r"\becological\s+information\b": 2.0,
        r"\bdisposal\s+considerations\b": 2.0,
        r"\btransport\s+information\b": 2.0,
        r"\bcas\s*(?:no\.?|number|#)?\s*[:\d\-]+": 2.0,
        r"\bsignal\s+word\s*:\s*(danger|warning)\b": 2.5,
        r"\b(h\d{3}|p\d{3})\b": 1.5,
    },
    DocumentGenre.SOP: {
        r"\bstandard\s+operating\s+procedure\b": 3.0,
        r"\bsop\s*(?:no\.?|number|#|id)\b": 2.5,
        r"\bpurpose\s+and\s+scope\b": 2.0,
        r"\bresponsibilities?\b": 1.5,
        r"\bprocedure\s+steps?\b": 2.0,
        r"\bequipment\s+and\s+(reagents|materials)\b": 2.0,
        r"\brevision\s+history\b": 2.0,
        r"\bapproval\s+signatures?\b": 2.0,
        r"\beffective\s+date\b": 1.5,
        r"\bsupersedes\b": 1.5,
    },
    DocumentGenre.EXPERIMENTAL_REPORT: {
        r"\blaboratory\s+notebook\b": 3.0,
        r"\bexperimental\s+report\b": 3.0,
        r"\bbatch\s*(?:no\.?|number|#)\b": 2.0,
        r"\blot\s*(?:no\.?|number|#)\b": 2.0,
        r"\breaction\s+scheme\b": 2.0,
        r"\byield\s*:\s*\d+": 2.0,
        r"\bcrude\s+product\b": 2.0,
        r"\bpurification\s+method\b": 1.5,
        r"\banalytical\s+data\b": 1.5,
        r"\b1h-?nmr\b": 2.0,
        r"\bhplc\s+analysis\b": 2.0,
        r"\brun\s*(?:no\.?|number|#)\b": 1.5,
    },
    DocumentGenre.RESEARCH_PAPER: {
        r"\babstract\b": 2.0,
        r"\bmaterials\s+and\s+methods\b": 2.5,
        r"\bexperimental\s+section\b": 2.0,
        r"\bresults\s+and\s+discussion\b": 2.5,
        r"\bconclusions?\b": 1.5,
        r"\breferences\b": 2.0,
        r"\bdoi\s*:\s*10\.\d{4,9}/": 3.0,
        r"\bcorresponding\s+author\b": 2.0,
        r"\belectronic\s+supplementary\s+information\b": 2.5,
        r"\bpeer-?reviewed\b": 1.5,
    },
    DocumentGenre.TEXTBOOK: {
        r"\bchapter\s+\d+\b": 2.5,
        r"\btable\s+of\s+contents\b": 2.5,
        r"\bindex\b": 1.5,
        r"\bexercises?\b": 2.0,
        r"\bproblems?\s+and\s+solutions?\b": 2.5,
        r"\bpreface\b": 2.0,
        r"\bedition\b": 1.5,
        r"\bisbn\b": 2.5,
    },
    DocumentGenre.TECHNICAL_REPORT: {
        r"\btechnical\s+report\b": 3.0,
        r"\bexecutive\s+summary\b": 2.5,
        r"\bproject\s+report\b": 2.0,
        r"\bdeliverable\s+d?\d+": 2.5,
        r"\bgrant\s+agreement\b": 2.0,
        r"\bcontract\s*(?:no\.?|number|#)\b": 2.0,
        r"\bprepared\s+for\b": 1.5,
    },
}


@dataclass
class ClassificationResult:
    """Result of document genre classification."""
    genre: DocumentGenre
    confidence: float
    parser_recommended: str
    scores: Dict[str, float] = field(default_factory=dict)
    matched_signals: List[str] = field(default_factory=list)
    classified_by: str = "heuristics"

    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.50 and self.genre != DocumentGenre.UNKNOWN


class DocumentClassifier:
    """
    Rule-based and structural document classifier with ML/VLM hook.
    """

    def __init__(self, confidence_threshold: float = 0.40) -> None:
        self.confidence_threshold = confidence_threshold

    def classify_text(
        self,
        text: str,
        filename: str = "",
        page_count: Optional[int] = None,
    ) -> ClassificationResult:
        """
        Classifies document based on text content, filename clues, and page count.
        """
        if not text and not filename:
            return ClassificationResult(
                genre=DocumentGenre.UNKNOWN,
                confidence=0.0,
                parser_recommended=GENRE_PARSER_MAP[DocumentGenre.UNKNOWN],
            )

        combined_text = f"{filename}\n{text}".lower()
        scores: Dict[str, float] = {g.value: 0.0 for g in GENRE_SIGNALS.keys()}
        matched_signals: List[str] = []

        # 1. Regex Heuristic Scoring
        for genre, signals in GENRE_SIGNALS.items():
            for pattern, weight in signals.items():
                matches = len(re.findall(pattern, combined_text, flags=re.IGNORECASE))
                if matches > 0:
                    matched_score = weight * min(matches, 3)  # capped contribution
                    scores[genre.value] += matched_score
                    matched_signals.append(f"{genre.value}:{pattern}:{matches}")

        # 2. Structural & Page Count Adjustments
        if page_count is not None:
            if page_count > 100:
                # Heavy bias towards textbook
                scores[DocumentGenre.TEXTBOOK.value] += 4.0
            elif page_count <= 16 and scores[DocumentGenre.SDS.value] > 2.0:
                # SDS typically 1-16 pages
                scores[DocumentGenre.SDS.value] += 2.0

        # 3. Filename Clues
        fname_lower = filename.lower()
        if "sds" in fname_lower or "msds" in fname_lower:
            scores[DocumentGenre.SDS.value] += 3.0
        if "sop" in fname_lower:
            scores[DocumentGenre.SOP.value] += 3.0
        if "report" in fname_lower:
            scores[DocumentGenre.TECHNICAL_REPORT.value] += 1.5

        # 4. Score Normalization & Winner Determination
        total_score = sum(scores.values())
        if total_score == 0:
            return ClassificationResult(
                genre=DocumentGenre.UNKNOWN,
                confidence=0.0,
                parser_recommended=GENRE_PARSER_MAP[DocumentGenre.UNKNOWN],
                scores=scores,
                matched_signals=[],
            )

        best_genre_str = max(scores, key=lambda k: scores[k])
        best_score = scores[best_genre_str]

        # Confidence: ratio of best score to total score with threshold dampening
        confidence = round(min(best_score / (total_score + 1.0), 1.0), 2)

        best_genre = DocumentGenre(best_genre_str)

        # Fallback if below confidence threshold
        if confidence < self.confidence_threshold:
            logger.info(
                "Document classification confidence below threshold; falling back to UNKNOWN",
                best_genre=best_genre.value,
                confidence=confidence,
                threshold=self.confidence_threshold,
            )
            return ClassificationResult(
                genre=DocumentGenre.UNKNOWN,
                confidence=confidence,
                parser_recommended=GENRE_PARSER_MAP[DocumentGenre.UNKNOWN],
                scores=scores,
                matched_signals=matched_signals,
            )

        return ClassificationResult(
            genre=best_genre,
            confidence=confidence,
            parser_recommended=GENRE_PARSER_MAP[best_genre],
            scores=scores,
            matched_signals=matched_signals,
        )

    async def classify_with_ml(
        self,
        text: str,
        filename: str = "",
        page_count: Optional[int] = None,
    ) -> ClassificationResult:
        """
        Pluggable ML/VLM classifier hook. Falls back to heuristics when ML is not enabled.
        """
        # Heuristics first
        result = self.classify_text(text, filename=filename, page_count=page_count)
        if result.is_confident:
            return result

        # In future phases (Phase 04+), an LLM or VLM call can refine low-confidence cases.
        return result
