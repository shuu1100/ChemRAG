"""
ChemRAG — Chemistry Domain Package
===================================
Chemical image detection, OCSR ensemble, RDKit validation, and reaction schemes.
"""
from __future__ import annotations

from backend.app.chemistry.image_classifier import (
    ChemicalImageClassifier,
    ImageCategory,
    ImageClassificationResult,
)
from backend.app.chemistry.ocsr.base import BaseOCSRProvider, OCSRResult
from backend.app.chemistry.ocsr.decimer import DecimerProvider
from backend.app.chemistry.ocsr.ensemble import EnsembleOCSRResult, EnsembleOCSRService
from backend.app.chemistry.ocsr.molscribe import MolScribeProvider
from backend.app.chemistry.reaction import (
    ParticipantRole,
    ReactionConditions,
    ReactionParticipant,
    ReactionScheme,
)
from backend.app.chemistry.validator import RDKitStructureValidator, StructureValidationResult

__all__ = [
    # Image Classification
    "ChemicalImageClassifier",
    "ImageCategory",
    "ImageClassificationResult",
    # Structure Validation
    "RDKitStructureValidator",
    "StructureValidationResult",
    # OCSR Providers
    "BaseOCSRProvider",
    "OCSRResult",
    "DecimerProvider",
    "MolScribeProvider",
    "EnsembleOCSRService",
    "EnsembleOCSRResult",
    # Reaction Schemes
    "ParticipantRole",
    "ReactionParticipant",
    "ReactionConditions",
    "ReactionScheme",
]
