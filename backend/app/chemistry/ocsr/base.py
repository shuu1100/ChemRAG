"""
ChemRAG — Modular Optical Chemical Structure Recognition (OCSR) Interface
==========================================================================
Unified interface for chemical structure recognition providers (DECIMER, MolScribe).
"""
from __future__ import annotations

import abc
import io
import time
from dataclasses import dataclass, field
from typing import Optional

from PIL import Image, ImageOps

from backend.app.chemistry.validator import StructureValidationResult


@dataclass
class OCSRResult:
    """Output from an OCSR engine prediction."""
    smiles: str
    confidence: float
    provider_name: str
    model_version: str
    processing_time_ms: float
    validation: Optional[StructureValidationResult] = None
    error: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        return self.validation is not None and self.validation.is_valid


class BaseOCSRProvider(abc.ABC):
    """Abstract interface for OCSR engines."""

    provider_name: str = "base"
    model_version: str = "1.0"

    def preprocess_image(self, image_bytes: bytes, target_size: int = 512) -> bytes:
        """
        Standardizes chemical structure image:
        - Convert to RGB
        - Add padding so bonds aren't touching edges
        - Contrast enhancement
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                rgb_img = img.convert("RGB")

                # Add a 20px white border
                bordered = ImageOps.expand(rgb_img, border=20, fill="white")

                # Resize maintaining aspect ratio
                bordered.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)

                out = io.BytesIO()
                bordered.save(out, format="PNG")
                return out.getvalue()
        except Exception:
            return image_bytes

    @abc.abstractmethod
    async def predict(self, image_bytes: bytes, image_id: str = "") -> OCSRResult:
        """Predict SMILES string from structure image."""
        ...
