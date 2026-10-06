"""
ChemRAG — Ensemble OCSR Service (DECIMER + MolScribe + RDKit)
=============================================================
Orchestrates primary OCSR (DECIMER) and fallback (MolScribe).
Validates predicted structures with RDKit.
Detects molecular graph disagreement between engines and flags uncertain cases for review.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from backend.app.chemistry.ocsr.base import BaseOCSRProvider, OCSRResult
from backend.app.chemistry.ocsr.decimer import DecimerProvider
from backend.app.chemistry.ocsr.molscribe import MolScribeProvider
from backend.app.chemistry.validator import RDKitStructureValidator, StructureValidationResult
from backend.app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class EnsembleOCSRResult:
    """Consolidated OCSR result with validation, agreement tracking, and review flags."""
    selected_smiles: Optional[str]
    canonical_smiles: Optional[str]
    inchi_key: Optional[str]
    confidence: float
    is_valid: bool
    primary_result: OCSRResult
    fallback_result: Optional[OCSRResult] = None
    has_disagreement: bool = False
    requires_review: bool = False
    comparison_notes: str = ""


class EnsembleOCSRService:
    """
    Combines DECIMER, MolScribe, and RDKit for robust chemical structure recognition.
    """

    def __init__(
        self,
        decimer: Optional[BaseOCSRProvider] = None,
        molscribe: Optional[BaseOCSRProvider] = None,
        validator: Optional[RDKitStructureValidator] = None,
        confidence_threshold: float = 0.80,
    ) -> None:
        self.decimer = decimer or DecimerProvider()
        self.molscribe = molscribe or MolScribeProvider()
        self.validator = validator or RDKitStructureValidator()
        self.confidence_threshold = confidence_threshold

    async def recognize_structure(
        self,
        image_bytes: bytes,
        image_id: str = "",
        force_dual_engine: bool = False,
    ) -> EnsembleOCSRResult:
        """
        Runs primary OCSR engine, validates output, and triggers fallback when needed.
        """
        # 1. Run DECIMER
        decimer_res = await self.decimer.predict(image_bytes, image_id)
        decimer_val = self.validator.validate_smiles(decimer_res.smiles)
        decimer_res.validation = decimer_val

        needs_fallback = (
            force_dual_engine
            or not decimer_val.is_valid
            or decimer_res.confidence < self.confidence_threshold
        )

        if not needs_fallback:
            # Confident, valid DECIMER prediction
            return EnsembleOCSRResult(
                selected_smiles=decimer_res.smiles,
                canonical_smiles=decimer_val.canonical_smiles,
                inchi_key=decimer_val.inchi_key,
                confidence=decimer_res.confidence,
                is_valid=True,
                primary_result=decimer_res,
                has_disagreement=False,
                requires_review=False,
                comparison_notes="DECIMER prediction validated by RDKit with high confidence.",
            )

        # 2. Run MolScribe Fallback
        logger.info(
            "Triggering MolScribe fallback",
            image_id=image_id,
            decimer_valid=decimer_val.is_valid,
            decimer_conf=decimer_res.confidence,
        )
        molscribe_res = await self.molscribe.predict(image_bytes, image_id)
        molscribe_val = self.validator.validate_smiles(molscribe_res.smiles)
        molscribe_res.validation = molscribe_val

        # Case A: Both engines produced valid structures -> compare them!
        if decimer_val.is_valid and molscribe_val.is_valid:
            is_match, match_detail = self.validator.compare_structures(
                decimer_res.smiles, molscribe_res.smiles
            )

            if is_match:
                # Strong consensus agreement!
                boosted_conf = min(0.99, max(decimer_res.confidence, molscribe_res.confidence) + 0.10)
                return EnsembleOCSRResult(
                    selected_smiles=decimer_res.smiles,
                    canonical_smiles=decimer_val.canonical_smiles,
                    inchi_key=decimer_val.inchi_key,
                    confidence=boosted_conf,
                    is_valid=True,
                    primary_result=decimer_res,
                    fallback_result=molscribe_res,
                    has_disagreement=False,
                    requires_review=False,
                    comparison_notes=f"Dual-engine consensus agreement: {match_detail}",
                )
            else:
                # Graph disagreement! Flag for review
                logger.warning(
                    "OCSR graph disagreement detected",
                    decimer_smiles=decimer_val.canonical_smiles,
                    molscribe_smiles=molscribe_val.canonical_smiles,
                )
                # Select the one with higher confidence, but mark requires_review
                selected = decimer_res if decimer_res.confidence >= molscribe_res.confidence else molscribe_res
                selected_val = selected.validation
                return EnsembleOCSRResult(
                    selected_smiles=selected.smiles,
                    canonical_smiles=selected_val.canonical_smiles if selected_val else None,
                    inchi_key=selected_val.inchi_key if selected_val else None,
                    confidence=selected.confidence,
                    is_valid=True,
                    primary_result=decimer_res,
                    fallback_result=molscribe_res,
                    has_disagreement=True,
                    requires_review=True,
                    comparison_notes=f"Conflict detected between DECIMER and MolScribe: {match_detail}",
                )

        # Case B: Only MolScribe is valid
        if molscribe_val.is_valid and not decimer_val.is_valid:
            return EnsembleOCSRResult(
                selected_smiles=molscribe_res.smiles,
                canonical_smiles=molscribe_val.canonical_smiles,
                inchi_key=molscribe_val.inchi_key,
                confidence=molscribe_res.confidence,
                is_valid=True,
                primary_result=decimer_res,
                fallback_result=molscribe_res,
                has_disagreement=True,
                requires_review=False,
                comparison_notes=f"DECIMER invalid ({decimer_val.error}); MolScribe succeeded.",
            )

        # Case C: Only DECIMER is valid
        if decimer_val.is_valid and not molscribe_val.is_valid:
            return EnsembleOCSRResult(
                selected_smiles=decimer_res.smiles,
                canonical_smiles=decimer_val.canonical_smiles,
                inchi_key=decimer_val.inchi_key,
                confidence=decimer_res.confidence,
                is_valid=True,
                primary_result=decimer_res,
                fallback_result=molscribe_res,
                has_disagreement=True,
                requires_review=False,
                comparison_notes=f"MolScribe invalid ({molscribe_val.error}); DECIMER succeeded.",
            )

        # Case D: Both engines produced invalid output
        return EnsembleOCSRResult(
            selected_smiles=None,
            canonical_smiles=None,
            inchi_key=None,
            confidence=0.0,
            is_valid=False,
            primary_result=decimer_res,
            fallback_result=molscribe_res,
            has_disagreement=False,
            requires_review=True,
            comparison_notes="Both DECIMER and MolScribe failed RDKit validation.",
        )
