"""
ChemRAG — Chemical Entity Normalization & Validation API Tests
==============================================================
Tests:
- CAS Registry number Modulo-10 checksum validation
- Chemical entity extraction from scientific text
- RDKit structure validation API endpoint
- PubChem caching, negative caching, and offline tolerance
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.app.chemistry.entity_extractor import (
    ChemicalEntityExtractor,
    ChemicalMentionType,
    verify_cas_checksum,
)
from backend.app.chemistry.pubchem_resolver import PubChemRecord, PubChemResolver
from backend.app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestCasChecksum:
    def test_valid_cas_checksums(self) -> None:
        # Standard verified CAS numbers
        assert verify_cas_checksum("50-00-0") is True     # Formaldehyde
        assert verify_cas_checksum("67-64-1") is True     # Acetone
        assert verify_cas_checksum("7732-18-5") is True   # Water
        assert verify_cas_checksum("58-08-2") is True     # Caffeine
        assert verify_cas_checksum("108-88-3") is True    # Toluene

    def test_invalid_cas_checksums(self) -> None:
        # Corrupted check digits
        assert verify_cas_checksum("50-00-1") is False
        assert verify_cas_checksum("67-64-9") is False
        assert verify_cas_checksum("7732-18-9") is False
        assert verify_cas_checksum("123-45") is False
        assert verify_cas_checksum("not-a-cas") is False


class TestChemicalEntityExtractor:
    def test_extract_all_entity_types(self) -> None:
        text = """
        The reaction of caffeine (CAS: 58-08-2, InChIKey: RYYVLZVUVIJVGH-UHFFFAOYSA-N)
        was conducted in anhydrous THF using Pd(PPh3)4 (0.05 eq) under 5.0 bar N2
        at 85 °C for 16 h to yield the desired product.
        """
        extractor = ChemicalEntityExtractor()
        mentions = extractor.extract_entities(text)

        types = {m.mention_type for m in mentions}
        assert ChemicalMentionType.CAS_NUMBER in types
        assert ChemicalMentionType.INCHI_KEY in types
        assert ChemicalMentionType.SOLVENT in types
        assert ChemicalMentionType.CATALYST in types
        assert ChemicalMentionType.PROCESS_CONDITION in types

        # Check normalization
        thf_mention = next(m for m in mentions if m.raw_text.upper() == "THF")
        assert thf_mention.normalized_text == "tetrahydrofuran"

        cat_mention = next(m for m in mentions if "pd(pph3)4" in m.raw_text.lower())
        assert "palladium" in cat_mention.normalized_text.lower()


class TestPubChemResolver:
    @pytest.mark.asyncio
    async def test_pubchem_caching_and_negative_caching(self) -> None:
        resolver = PubChemResolver(enabled=True)

        # Mock _fetch_compound_properties
        mock_record = PubChemRecord(
            cid=962,
            canonical_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
            inchi_key="BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
            iupac_name="2-acetyloxybenzoic acid",
            molecular_formula="C9H8O4",
            molecular_weight=180.16,
        )

        with patch.object(resolver, "_fetch_compound_properties", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_record

            # First call -> fetches from network
            res1 = await resolver.resolve_by_name("aspirin")
            assert res1 is not None
            assert res1.cid == 962
            assert mock_fetch.call_count == 1

            # Second call -> returned from in-memory cache!
            res2 = await resolver.resolve_by_name("aspirin")
            assert res2 is not None
            assert res2.cid == 962
            assert mock_fetch.call_count == 1  # Network NOT called again!

    @pytest.mark.asyncio
    async def test_pubchem_negative_caching(self) -> None:
        resolver = PubChemResolver(enabled=True)

        with patch.object(resolver, "_fetch_compound_properties", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None  # Compound not found (404)

            # First call -> 404 from network
            res1 = await resolver.resolve_by_name("nonexistent_chemical_xyz")
            assert res1 is None
            assert mock_fetch.call_count == 1

            # Second call -> negative cache hit, network not called again!
            res2 = await resolver.resolve_by_name("nonexistent_chemical_xyz")
            assert res2 is None
            assert mock_fetch.call_count == 1

    @pytest.mark.asyncio
    async def test_offline_mode_returns_none_gracefully(self) -> None:
        resolver = PubChemResolver(enabled=False)
        result = await resolver.resolve_by_name("benzene")
        assert result is None


class TestChemistryAPIEndpoints:
    def test_validate_valid_smiles(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/chemistry/validate",
            json={"smiles": "c1ccccc1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["canonical_smiles"] == "c1ccccc1"
        assert data["inchi_key"] == "UHOVQNZJYSORNB-UHFFFAOYSA-N"
        assert data["molecular_formula"] == "C6H6"
        assert data["heavy_atom_count"] == 6
        assert data["bond_count"] == 6
        assert data["validation_error"] is None

    def test_validate_invalid_smiles(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/chemistry/validate",
            json={"smiles": "C(=C)(=C)(=C)=C=C"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert data["validation_error"] is not None

    def test_extract_entities_endpoint(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/chemistry/extract-entities",
            json={"text": "Acetone (CAS: 67-64-1) was heated to 56 °C."},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 2
        raw_texts = [m["raw_text"] for m in data["mentions"]]
        assert "67-64-1" in raw_texts
        assert any("56" in t for t in raw_texts)
