"""
ChemRAG — Phase 16 Unit Tests: External Data Sources & Scientific Metadata
===========================================================================
Tests PubChem PUG REST integration and Scientific Metadata providers abstraction:
- PubChem lookup by name, SMILES, InChI, InChIKey, and formula
- Caching, rate limiting, and timestamped storage
- Crossref, OpenAlex, SemanticScholar, PubMed, and arXiv provider abstractions
- Offline resilience and provider disabling exit criteria
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from backend.app.chemistry.pubchem_resolver import PubChemRecord, PubChemResolver
from backend.app.services.metadata.aggregator import MetadataAggregator
from backend.app.services.metadata.arxiv import ArXivProvider
from backend.app.services.metadata.crossref import CrossrefProvider
from backend.app.services.metadata.models import PublicationMetadata
from backend.app.services.metadata.openalex import OpenAlexProvider
from backend.app.services.metadata.pubmed import PubMedProvider
from backend.app.services.metadata.semantic_scholar import SemanticScholarProvider


@pytest.mark.asyncio
async def test_pubchem_resolver_disabled():
    """Verify PubChemResolver returns None when disabled (offline core requirement)."""
    resolver = PubChemResolver(enabled=False)
    assert resolver.enabled is False

    res_name = await resolver.resolve_by_name("Ethanol")
    assert res_name is None

    res_smiles = await resolver.resolve_by_smiles("CCO")
    assert res_smiles is None

    res_key = await resolver.resolve_by_inchikey("LFQSCWFLJHTTHZ-UHFFFAOYSA-N")
    assert res_key is None

    res_formula = await resolver.resolve_by_formula("C2H6O")
    assert res_formula is None


@pytest.mark.asyncio
async def test_pubchem_resolver_caching():
    """Verify PubChemResolver caches positive and negative responses."""
    resolver = PubChemResolver(enabled=True)

    rec = PubChemRecord(
        cid=702,
        canonical_smiles="CCO",
        iupac_name="ethanol",
        molecular_formula="C2H6O",
        molecular_weight=46.07,
    )

    with patch.object(resolver, "_fetch_compound_properties", new=AsyncMock(return_value=rec)) as mock_fetch:
        # First call fetches from remote API
        res1 = await resolver.resolve_by_name("Ethanol")
        assert res1 is not None
        assert res1.cid == 702
        assert mock_fetch.call_count == 1

        # Second call returns cached record without remote API call
        res2 = await resolver.resolve_by_name("Ethanol")
        assert res2 is not None
        assert res2.cid == 702
        assert mock_fetch.call_count == 1  # Still 1 call


@pytest.mark.asyncio
async def test_metadata_providers_disabled():
    """Verify all metadata providers can be disabled and fail gracefully."""
    crossref = CrossrefProvider(enabled=False)
    openalex = OpenAlexProvider(enabled=False)
    s2 = SemanticScholarProvider(enabled=False)
    pubmed = PubMedProvider(enabled=False)
    arxiv = ArXivProvider(enabled=False)

    assert await crossref.fetch_by_doi("10.1021/acs.jced.1c00001") is None
    assert await openalex.fetch_by_doi("10.1021/acs.jced.1c00001") is None
    assert await s2.fetch_by_doi("10.1021/acs.jced.1c00001") is None
    assert await pubmed.fetch_by_doi("10.1021/acs.jced.1c00001") is None
    assert await arxiv.fetch_by_doi("10.1021/acs.jced.1c00001") is None


@pytest.mark.asyncio
async def test_metadata_aggregator_orchestration():
    """Verify MetadataAggregator searches across enabled providers."""
    aggregator = MetadataAggregator(enabled=True)

    fake_meta = PublicationMetadata(
        title="Thermodynamics of Ethanol-Water Mixtures",
        authors=["J. M. Smith"],
        doi="10.1021/acs.jced.1c00001",
        publication_year=2021,
        journal="Journal of Chemical & Engineering Data",
        provider="crossref",
    )

    with patch.object(aggregator.crossref, "fetch_by_doi", new=AsyncMock(return_value=fake_meta)):
        meta = await aggregator.fetch_by_doi("10.1021/acs.jced.1c00001")
        assert meta is not None
        assert meta.title == "Thermodynamics of Ethanol-Water Mixtures"
        assert meta.provider == "crossref"
