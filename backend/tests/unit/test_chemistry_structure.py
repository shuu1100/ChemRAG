"""
ChemRAG — Chemical Structure Recognition & Validation Tests
============================================================
Tests:
- Chemical image candidate detection vs ordinary images
- Modular OCSR providers (DECIMER and MolScribe)
- RDKit structure validation and canonicalization
- Conflicting OCSR result detection and flagging
- Structured reaction scheme representation
"""
from __future__ import annotations

import io
from unittest.mock import AsyncMock
import pytest
from PIL import Image, ImageDraw

from backend.app.chemistry.image_classifier import (
    ChemicalImageClassifier,
    ImageCategory,
)
from backend.app.chemistry.ocsr.base import OCSRResult
from backend.app.chemistry.ocsr.decimer import DecimerProvider
from backend.app.chemistry.ocsr.ensemble import EnsembleOCSRService
from backend.app.chemistry.ocsr.molscribe import MolScribeProvider
from backend.app.chemistry.reaction import (
    ParticipantRole,
    ReactionConditions,
    ReactionParticipant,
    ReactionScheme,
)
from backend.app.chemistry.validator import RDKitStructureValidator


def create_sample_drawing_image(width: int = 300, height: int = 250) -> bytes:
    """Generate in-memory white background image with black skeletal drawing."""
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)
    # Draw simple polygon representing a benzene ring
    draw.line([(100, 80), (150, 50), (200, 80), (200, 140), (150, 170), (100, 140), (100, 80)], fill="black", width=3)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def create_dense_photo_image(width: int = 300, height: int = 250) -> bytes:
    """Generate in-memory continuous tone image resembling a photograph."""
    img = Image.new("RGB", (width, height), color="gray")
    draw = ImageDraw.Draw(img)
    for i in range(0, width, 5):
        draw.line([(i, 0), (i, height)], fill=(i % 255, (i * 2) % 255, 120))
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


class TestChemicalImageDetection:
    def test_detects_molecular_structure_from_drawing(self) -> None:
        classifier = ChemicalImageClassifier()
        img_bytes = create_sample_drawing_image()
        result = classifier.classify(img_bytes, caption="Figure 1: Molecular structure of compound 4a")

        assert result.category == ImageCategory.MOLECULAR_STRUCTURE
        assert result.is_candidate_for_ocsr is True
        assert result.confidence >= 0.70

    def test_detects_reaction_scheme_from_caption(self) -> None:
        classifier = ChemicalImageClassifier()
        img_bytes = create_sample_drawing_image(width=500, height=200)
        result = classifier.classify(img_bytes, caption="Scheme 2: Catalytic pathway for cross-coupling")

        assert result.category == ImageCategory.REACTION_SCHEME
        assert result.is_candidate_for_ocsr is True

    def test_rejects_ordinary_photograph(self) -> None:
        classifier = ChemicalImageClassifier()
        img_bytes = create_dense_photo_image()
        result = classifier.classify(img_bytes, caption="Photograph of laboratory equipment")

        assert result.is_candidate_for_ocsr is False
        assert result.category in (ImageCategory.PHOTOGRAPH, ImageCategory.ORDINARY_IMAGE)


class TestRDKitValidator:
    def test_valid_smiles_canonicalization(self) -> None:
        validator = RDKitStructureValidator()
        # Aspirin raw SMILES
        raw_smiles = "CC(=O)Oc1ccccc1C(=O)O"
        result = validator.validate_smiles(raw_smiles)

        assert result.is_valid is True
        assert result.canonical_smiles == "CC(=O)Oc1ccccc1C(=O)O"
        assert result.inchi_key is not None
        assert result.molecular_formula == "C9H8O4"
        assert result.molecular_weight in (180.042, 180.157)
        assert result.heavy_atom_count == 13

        assert result.ring_count == 1

    def test_invalid_smiles_rejected(self) -> None:
        validator = RDKitStructureValidator()
        # Chemically impossible 5-valent carbon without charge or bad syntax
        bad_smiles = "C(=C)(=C)(=C)=C=C"
        result = validator.validate_smiles(bad_smiles)
        assert result.is_valid is False
        assert result.error is not None

    def test_structure_equivalence_comparison(self) -> None:
        validator = RDKitStructureValidator()
        # Different representations of ethanol
        smiles_1 = "CCO"
        smiles_2 = "OCC"
        is_same, msg = validator.compare_structures(smiles_1, smiles_2)
        assert is_same is True
        assert "Identical" in msg

    def test_detects_graph_disagreement(self) -> None:
        validator = RDKitStructureValidator()
        # Ethanol vs Methanol
        smiles_a = "CCO"
        smiles_b = "CO"
        is_same, msg = validator.compare_structures(smiles_a, smiles_b)
        assert is_same is False
        assert "disagreement" in msg.lower()


class TestModularOCSRProviders:
    @pytest.mark.asyncio
    async def test_decimer_provider_modular_interface(self) -> None:
        decimer = DecimerProvider()
        img_bytes = create_sample_drawing_image()
        res = await decimer.predict(img_bytes, image_id="img-001")

        assert isinstance(res, OCSRResult)
        assert res.provider_name == "DECIMER"
        assert res.confidence > 0.0
        assert res.processing_time_ms >= 0.0

    @pytest.mark.asyncio
    async def test_molscribe_provider_modular_interface(self) -> None:
        molscribe = MolScribeProvider()
        img_bytes = create_sample_drawing_image()
        res = await molscribe.predict(img_bytes, image_id="img-002")

        assert isinstance(res, OCSRResult)
        assert res.provider_name == "MolScribe"
        assert res.confidence > 0.0


class TestEnsembleOCSRAndConflictDetection:
    @pytest.mark.asyncio
    async def test_ensemble_consensus_agreement(self) -> None:
        # Mock DECIMER and MolScribe to return equivalent benzene SMILES
        decimer_mock = AsyncMock()
        decimer_mock.predict.return_value = OCSRResult(
            smiles="c1ccccc1", confidence=0.85, provider_name="DECIMER", model_version="2.3", processing_time_ms=50
        )
        molscribe_mock = AsyncMock()
        molscribe_mock.predict.return_value = OCSRResult(
            smiles="C1=CC=CC=C1", confidence=0.88, provider_name="MolScribe", model_version="1.1", processing_time_ms=40
        )

        ensemble = EnsembleOCSRService(decimer=decimer_mock, molscribe=molscribe_mock)
        img_bytes = create_sample_drawing_image()

        result = await ensemble.recognize_structure(img_bytes, force_dual_engine=True)

        assert result.is_valid is True
        assert result.has_disagreement is False
        assert result.requires_review is False
        assert result.confidence >= 0.95  # Consensus confidence boost!
        assert result.canonical_smiles == "c1ccccc1"

    @pytest.mark.asyncio
    async def test_flags_conflicting_ocsr_results(self) -> None:
        # Mock DECIMER predicting Benzene, MolScribe predicting Pyridine
        decimer_mock = AsyncMock()
        decimer_mock.predict.return_value = OCSRResult(
            smiles="c1ccccc1", confidence=0.75, provider_name="DECIMER", model_version="2.3", processing_time_ms=50
        )
        molscribe_mock = AsyncMock()
        molscribe_mock.predict.return_value = OCSRResult(
            smiles="c1ccncc1", confidence=0.72, provider_name="MolScribe", model_version="1.1", processing_time_ms=45
        )

        ensemble = EnsembleOCSRService(decimer=decimer_mock, molscribe=molscribe_mock)
        img_bytes = create_sample_drawing_image()

        result = await ensemble.recognize_structure(img_bytes, force_dual_engine=True)

        assert result.is_valid is True
        assert result.has_disagreement is True
        assert result.requires_review is True
        assert "Conflict detected" in result.comparison_notes


class TestReactionSchemeRepresentation:
    def test_reaction_representation_formatting(self) -> None:
        reaction = ReactionScheme(
            scheme_id="SCHEME-1",
            title="Suzuki-Miyaura Cross-Coupling",
            reactants=[
                ReactionParticipant(name="4-bromotoluene", smiles="c1cc(ccc1C)Br", role=ParticipantRole.REACTANT),
                ReactionParticipant(name="phenylboronic acid", smiles="B(c1ccccc1)(O)O", role=ParticipantRole.REACTANT),
            ],
            products=[
                ReactionParticipant(name="4-methylbiphenyl", smiles="c1ccc(cc1)c2ccc(cc2)C", role=ParticipantRole.PRODUCT),
            ],
            catalysts=[
                ReactionParticipant(name="Pd(PPh3)4", role=ParticipantRole.CATALYST),
            ],
            reagents=[
                ReactionParticipant(name="K2CO3", role=ParticipantRole.REAGENT, amount="2.0 equiv"),
            ],
            solvents=[
                ReactionParticipant(name="1,4-dioxane/water (4:1)", role=ParticipantRole.SOLVENT),
            ],
            conditions=ReactionConditions(
                temperature_celsius=90.0,
                time_hours=12.0,
                atmosphere="N2",
            ),
            yield_pct=92.5,
            source_citation="J. Am. Chem. Soc. 2024, 146, 1234",
            page_number=3,
        )

        summary = reaction.to_retrieval_summary()
        assert "[Reaction Scheme: Suzuki-Miyaura Cross-Coupling]" in summary
        assert "Reactants: 4-bromotoluene" in summary
        assert "Products: 4-methylbiphenyl" in summary
        assert "Catalysts: Pd(PPh3)4" in summary
        assert "Conditions: 90.0 °C, 12.0 h, N2 atmosphere" in summary
        assert "Yield: 92.5%" in summary

        # JSON representation
        dict_rep = reaction.to_dict()
        assert dict_rep["scheme_id"] == "SCHEME-1"
        assert len(dict_rep["reactants"]) == 2
        assert len(dict_rep["products"]) == 1
        assert dict_rep["yield_pct"] == 92.5
