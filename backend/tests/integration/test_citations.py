"""
ChemRAG — Phase 13 Citations & Provenance Integration Tests
=============================================================
Tests:
- Prompt 13.1: Citation Engine stable CIT-xxx assignment and prompt formatting
- Prompt 13.2: Citation Validator claim extraction, entailment, invalid IDs, and hallucination detection
- Prompt 13.3: PDF.js Evidence Mapping viewport coordinate conversions & rotation/zoom scaling
- FastAPI citation endpoints (/api/v1/citations/*)
"""
from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from backend.app.citations.engine import CitationEngine
from backend.app.citations.evidence_mapper import EvidenceMapper
from backend.app.citations.models import (
    CitationMetadata,
    EvidenceMappingRequest,
)
from backend.app.citations.validator import CitationValidator
from backend.app.main import app
from backend.app.retrieval.models import ScoredChunk


@pytest.fixture
def sample_scored_chunks() -> list[ScoredChunk]:
    doc_id = uuid.uuid4()
    return [
        ScoredChunk(
            chunk_id=uuid.uuid4(),
            document_id=doc_id,
            content="Ethanol (C2H6O) has a boiling point of 78.37 °C and density of 0.789 g/cm³.",
            score=0.95,
            page_number=3,
            bbox={"x0": 50.0, "y0": 120.0, "x1": 500.0, "y1": 180.0},
            metadata={"document_title": "Thermodynamics of Ethanol", "section_title": "Properties", "doi": "10.1021/acs.jced.1c00001"},
        ),
        ScoredChunk(
            chunk_id=uuid.uuid4(),
            document_id=doc_id,
            content="The reaction rate constant k for catalytic hydrogenation was measured at 0.045 s⁻¹ at 300 K.",
            score=0.88,
            page_number=5,
            bbox={"x0": 60.0, "y0": 200.0, "x1": 480.0, "y1": 260.0},
            metadata={"document_title": "Reaction Kinetics Study", "section_title": "Kinetics", "doi": "10.1021/acs.jced.1c00002"},
        ),
    ]


class TestCitationEngine:
    """Tests for Prompt 13.1 — Citation Engine."""

    def test_assign_citations(self, sample_scored_chunks: list[ScoredChunk]) -> None:
        engine = CitationEngine()
        citations = engine.assign_citations(sample_scored_chunks)

        assert len(citations) == 2
        assert citations[0].citation_id == "CIT-001"
        assert citations[1].citation_id == "CIT-002"
        assert citations[0].page_number == 3
        assert citations[0].doi == "10.1021/acs.jced.1c00001"
        assert "78.37 °C" in citations[0].raw_text

    def test_format_context_with_citations(self, sample_scored_chunks: list[ScoredChunk]) -> None:
        engine = CitationEngine()
        citations = engine.assign_citations(sample_scored_chunks)
        context_str = engine.format_context_with_citations(citations)

        assert "[CIT-001]" in context_str
        assert "[CIT-002]" in context_str
        assert "Thermodynamics of Ethanol" in context_str
        assert "Page: 3" in context_str

    def test_resolve_citation(self, sample_scored_chunks: list[ScoredChunk]) -> None:
        engine = CitationEngine()
        citations = engine.assign_citations(sample_scored_chunks)

        resolved = engine.resolve_citation("[CIT-001]", citations)
        assert resolved is not None
        assert resolved.citation_id == "CIT-001"

        resolved_plain = engine.resolve_citation("CIT-002", citations)
        assert resolved_plain is not None
        assert resolved_plain.citation_id == "CIT-002"

        assert engine.resolve_citation("CIT-999", citations) is None


class TestCitationValidator:
    """Tests for Prompt 13.2 — Citation Validator."""

    def test_valid_response(self, sample_scored_chunks: list[ScoredChunk]) -> None:
        engine = CitationEngine()
        citations = engine.assign_citations(sample_scored_chunks)
        validator = CitationValidator()

        llm_response = "Ethanol has a boiling point of 78.37 °C [CIT-001]. The reaction rate constant was 0.045 s⁻¹ at 300 K [CIT-002]."
        res = validator.validate_response(llm_response, citations)

        assert res.is_valid is True
        assert len(res.invalid_citation_ids) == 0
        assert res.supported_claims_count == 2
        assert res.should_regenerate is False

    def test_invalid_citation_id_detection(self, sample_scored_chunks: list[ScoredChunk]) -> None:
        engine = CitationEngine()
        citations = engine.assign_citations(sample_scored_chunks)
        validator = CitationValidator()

        llm_response = "Ethanol boiling point is 78.37 °C [CIT-999]."
        res = validator.validate_response(llm_response, citations)

        assert res.is_valid is False
        assert "CIT-999" in res.invalid_citation_ids
        assert res.should_regenerate is True

    def test_uncited_factual_claim_detection(self, sample_scored_chunks: list[ScoredChunk]) -> None:
        engine = CitationEngine()
        citations = engine.assign_citations(sample_scored_chunks)
        validator = CitationValidator()

        llm_response = "Ethanol boils at 78.37 °C. The density is 0.789 g/cm³."
        res = validator.validate_response(llm_response, citations)

        assert res.uncited_claims_count >= 1
        assert len(res.warnings) > 0


class TestEvidenceMapper:
    """Tests for Prompt 13.3 — PDF.js Evidence Mapping."""

    def test_viewport_coord_conversion(self) -> None:
        mapper = EvidenceMapper()
        bbox = {"x0": 61.2, "y0": 79.2, "x1": 306.0, "y1": 158.4}

        coords = mapper.calculate_viewport_coords(
            bbox=bbox,
            viewport_width=800.0,
            viewport_height=1100.0,
            zoom_scale=1.0,
            rotation_degrees=0,
            page_width_pts=612.0,
            page_height_pts=792.0,
        )

        assert coords.x_pct == pytest.approx(10.0, abs=0.1)
        assert coords.y_pct == pytest.approx(10.0, abs=0.1)
        assert coords.width_pct == pytest.approx(40.0, abs=0.1)
        assert coords.height_pct == pytest.approx(10.0, abs=0.1)
        assert coords.viewport_x0 == pytest.approx(80.0, abs=1.0)

    def test_map_evidence_response(self) -> None:
        mapper = EvidenceMapper()
        cit = CitationMetadata(
            citation_id="CIT-001",
            chunk_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            document_title="Ethanol Study",
            page_number=3,
            bbox={"x0": 50.0, "y0": 100.0, "x1": 500.0, "y1": 200.0},
            raw_text="Ethanol properties snippet",
            doi="10.1021/acs.jced.1c00001",
        )
        req = EvidenceMappingRequest(
            citation_id="CIT-001",
            viewport_width=800.0,
            viewport_height=1100.0,
        )

        resp = mapper.map_evidence(cit, req)

        assert resp.citation_id == "CIT-001"
        assert resp.page_number == 3
        assert "/documents/" in resp.pdf_asset_url
        assert resp.viewport_coords.x_pct > 0.0


@pytest.mark.asyncio
async def test_citations_api_endpoints(sample_scored_chunks: list[ScoredChunk]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Test /api/v1/citations/assign
        chunks_payload = [
            {
                "chunk_id": str(sample_scored_chunks[0].chunk_id),
                "document_id": str(sample_scored_chunks[0].document_id),
                "content": sample_scored_chunks[0].content,
                "score": 0.95,
                "page_number": 3,
                "metadata": {"document_title": "Ethanol Study"},
            }
        ]
        assign_resp = await client.post("/api/v1/citations/assign", json={"chunks": chunks_payload})
        assert assign_resp.status_code == 200
        assign_data = assign_resp.json()
        assert len(assign_data["citations"]) == 1
        assert assign_data["citations"][0]["citation_id"] == "CIT-001"
        assert "[CIT-001]" in assign_data["llm_context_text"]

        # Test /api/v1/citations/validate
        cits = assign_data["citations"]
        validate_payload = {
            "generated_text": "Ethanol boils at 78.37 °C [CIT-001].",
            "valid_citations": cits,
        }
        val_resp = await client.post("/api/v1/citations/validate", json=validate_payload)
        assert val_resp.status_code == 200
        val_data = val_resp.json()
        assert val_data["is_valid"] is True
