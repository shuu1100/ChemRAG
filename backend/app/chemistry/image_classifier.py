"""
ChemRAG — Chemical Image Classifier & Candidate Detector
=========================================================
Classifies document image assets into:
MOLECULAR_STRUCTURE, REACTION_SCHEME, PLOT, PHOTOGRAPH, DIAGRAM, ORDINARY_IMAGE.

Filters images so OCSR is NOT run blindly over every image.
"""
from __future__ import annotations

import enum
import io
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from PIL import Image

from backend.app.core.logging import get_logger

logger = get_logger(__name__)


class ImageCategory(str, enum.Enum):
    MOLECULAR_STRUCTURE = "molecular_structure"
    REACTION_SCHEME = "reaction_scheme"
    PLOT = "plot"
    PHOTOGRAPH = "photograph"
    DIAGRAM = "diagram"
    ORDINARY_IMAGE = "ordinary_image"


@dataclass
class ImageClassificationResult:
    """Outcome of chemical image classification."""
    category: ImageCategory
    confidence: float
    is_candidate_for_ocsr: bool
    reasons: List[str] = field(default_factory=list)


# Text clues in captions or surrounding text
CAPTION_RULES = {
    ImageCategory.REACTION_SCHEME: [
        r"\bscheme\s+\d+\b",
        r"\breaction\s+scheme\b",
        r"\bsynthesis\s+of\b",
        r"\bpathway\b",
        r"\breagents?\s+and\s+conditions\b",
    ],
    ImageCategory.MOLECULAR_STRUCTURE: [
        r"\bstructure\s+(?:of|\d+)\b",
        r"\bcompound\s+\d+\b",
        r"\bchemical\s+structure\b",
        r"\bmolecular\s+formula\b",
    ],
    ImageCategory.PLOT: [
        r"\bspectra\b",
        r"\bspectrum\b",
        r"\bchromatogram\b",
        r"\bnmr\b",
        r"\bhplc\b",
        r"\bft-?ir\b",
        r"\bplot\b",
        r"\bcurve\b",
        r"\babsorbance\b",
        r"\btransmittance\b",
    ],
    ImageCategory.PHOTOGRAPH: [
        r"\bmicrograph\b",
        r"\bsem\b",
        r"\btem\b",
        r"\bafm\b",
        r"\bx-ray\s+crystal\b",
        r"\bphotograph\b",
    ],
}


class ChemicalImageClassifier:
    """
    Determines whether an image is a chemical structure or reaction scheme
    before invoking compute-heavy OCSR models.
    """

    def classify(
        self,
        image_bytes: bytes,
        caption: str = "",
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> ImageClassificationResult:
        reasons: List[str] = []

        # 1. Caption-based heuristic analysis
        cap_lower = caption.lower().strip()
        if cap_lower:
            for cat, patterns in CAPTION_RULES.items():
                for pat in patterns:
                    if re.search(pat, cap_lower, re.IGNORECASE):
                        reasons.append(f"Caption matched '{pat}'")
                        is_candidate = cat in (ImageCategory.MOLECULAR_STRUCTURE, ImageCategory.REACTION_SCHEME)
                        return ImageClassificationResult(
                            category=cat,
                            confidence=0.88,
                            is_candidate_for_ocsr=is_candidate,
                            reasons=reasons,
                        )

        # 2. Image property analysis using PIL
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                w, h = img.size
                aspect_ratio = float(w) / max(1.0, float(h))
                mode = img.mode

                # Convert to grayscale to check histogram & contrast
                gray = img.convert("L")
                colors = gray.getcolors(maxcolors=256)
                num_distinct_grays = len(colors) if colors else 256

                # Molecular structures typically have mostly white background with sharp black lines
                hist = gray.histogram()
                total_pixels = w * h
                white_pixels = sum(hist[230:])  # near white
                black_pixels = sum(hist[:50])   # near black
                mid_pixels = total_pixels - white_pixels - black_pixels

                white_ratio = white_pixels / total_pixels
                black_ratio = black_pixels / total_pixels
                mid_ratio = mid_pixels / total_pixels

                # Reaction schemes are typically wide aspect ratios with high white backgrounds
                if aspect_ratio >= 1.6 and white_ratio > 0.70 and black_ratio > 0.01:
                    reasons.append(f"Wide aspect ratio {aspect_ratio:.2f} with sparse lines on white background")
                    return ImageClassificationResult(
                        category=ImageCategory.REACTION_SCHEME,
                        confidence=0.75,
                        is_candidate_for_ocsr=True,
                        reasons=reasons,
                    )

                # Molecular structures: moderate aspect ratio, clean white background, line drawing
                if 0.5 <= aspect_ratio < 1.6 and white_ratio > 0.65 and black_ratio > 0.01 and mid_ratio < 0.25:
                    reasons.append(f"Line drawing on white background (white={white_ratio:.2f}, black={black_ratio:.2f})")
                    return ImageClassificationResult(
                        category=ImageCategory.MOLECULAR_STRUCTURE,
                        confidence=0.78,
                        is_candidate_for_ocsr=True,
                        reasons=reasons,
                    )

                # Continuous tone images (photographs, dense plots)
                if mid_ratio > 0.50 or (mode in ("RGB", "RGBA") and num_distinct_grays > 150 and white_ratio < 0.40):
                    reasons.append("High continuous tonal range indicating photograph or complex render")
                    return ImageClassificationResult(
                        category=ImageCategory.PHOTOGRAPH,
                        confidence=0.70,
                        is_candidate_for_ocsr=False,
                        reasons=reasons,
                    )

        except Exception as exc:
            logger.debug("PIL image analysis error, defaulting to ORDINARY_IMAGE", error=str(exc))
            reasons.append(f"Image inspection failed: {exc}")

        # Default fallback
        return ImageClassificationResult(
            category=ImageCategory.ORDINARY_IMAGE,
            confidence=0.50,
            is_candidate_for_ocsr=False,
            reasons=reasons or ["No chemical indicators detected"],
        )
