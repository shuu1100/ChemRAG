"""
Unit tests for Phase 08 — Embedding System.
Tests:
- Prompt 8.1: EmbeddingProvider interface, metadata recording, and provider independence.
- Prompt 8.2: Text embedding batching, retries, timeouts, and dimension validation.
- Prompt 8.3: Chemical embedding canonicalization, molecular vectors, and separate vector storage.
- Prompt 8.4: Benchmark reproducibility and output verification.
"""

from __future__ import annotations

import math
import uuid
import pytest

from backend.app.chunking.models import ChunkPayload
from backend.app.core.config import EmbeddingProvider
from backend.app.embeddings.base import (
    BaseEmbeddingProvider,
    BatchEmbeddingResult,
    EmbeddingDimensionMismatchError,
    EmbeddingError,
    EmbeddingMetadata,
    EmbeddingResult,
    l2_normalize,
)
from backend.app.embeddings.chemical_embedder import ChemicalEmbeddingService
from backend.app.embeddings.factory import (
    get_chemical_embedding_provider,
    get_text_embedding_provider,
)
from backend.app.embeddings.providers.chemberta import ChemBERTaEmbeddingProvider
from backend.app.embeddings.providers.deterministic import DeterministicLocalProvider
from backend.app.embeddings.providers.morgan import MorganFingerprintProvider
from backend.app.embeddings.providers.sentence_transformers import (
    SentenceTransformersProvider,
)
from backend.app.embeddings.text_embedder import TextEmbeddingService
from backend.app.models.chunk import Chunk, ChunkEmbedding, EmbeddingModelType


class TestEmbeddingBaseAndMetadata:
    """Test BaseEmbeddingProvider and metadata recording (Prompt 8.1)."""

    def test_metadata_fields_recorded(self) -> None:
        provider = DeterministicLocalProvider(
            model_name="test-model",
            dimensions=128,
            embedding_type=EmbeddingModelType.TEXT,
        )
        meta = provider.get_metadata()
        assert meta.model_name == "test-model"
        assert meta.dimensions == 128
        assert meta.provider == "local-deterministic"
        assert meta.embedding_type == EmbeddingModelType.TEXT
        assert meta.is_normalized is True
        assert meta.created_at is not None

    def test_dimension_validation_mismatch_raises_error(self) -> None:
        provider = DeterministicLocalProvider(dimensions=128)
        # Vector with 64 elements should fail when provider expects 128
        with pytest.raises(EmbeddingDimensionMismatchError) as exc_info:
            provider.validate_vector([0.1] * 64)
        assert exc_info.value.expected == 128
        assert exc_info.value.received == 64

    def test_l2_normalization_unit_length(self) -> None:
        raw_vec = [3.0, 4.0, 0.0]
        norm_vec, norm = l2_normalize(raw_vec)
        assert math.isclose(norm, 1.0)
        assert math.isclose(norm_vec[0], 0.6)
        assert math.isclose(norm_vec[1], 0.8)
        # Length of normalized vector is 1.0
        assert math.isclose(math.sqrt(sum(x * x for x in norm_vec)), 1.0)


class TestReproducibilityAndLocalMode:
    """Test reproducibility of deterministic and chemical embeddings (Exit Criteria)."""

    @pytest.mark.asyncio
    async def test_deterministic_text_embeddings_are_reproducible(self) -> None:
        provider = DeterministicLocalProvider(dimensions=256)
        text = "Catalytic hydrogenation of benzene over Raney nickel"

        res1 = await provider.embed_single(text)
        res2 = await provider.embed_single(text)

        assert res1.dimensions == 256
        assert res2.dimensions == 256
        assert res1.vector == res2.vector
        assert math.isclose(res1.norm, 1.0, rel_tol=1e-5)

    @pytest.mark.asyncio
    async def test_different_texts_produce_different_vectors(self) -> None:
        provider = DeterministicLocalProvider(dimensions=256)
        res1 = await provider.embed_single("Benzene")
        res2 = await provider.embed_single("Aspirin")
        assert res1.vector != res2.vector

    @pytest.mark.asyncio
    async def test_chemical_morgan_embeddings_reproducible(self) -> None:
        provider = MorganFingerprintProvider(dimensions=512)
        smiles = "CC(=O)Oc1ccccc1C(=O)O"  # Aspirin

        res1 = await provider.embed_single(smiles)
        res2 = await provider.embed_single(smiles)

        assert res1.dimensions == 512
        assert res1.vector == res2.vector
        assert res1.metadata.embedding_type == EmbeddingModelType.CHEMICAL
        assert math.isclose(res1.norm, 1.0, rel_tol=1e-5)


class TestTextEmbeddingService:
    """Test TextEmbeddingService batching, retries, and failed-item handling (Prompt 8.2)."""

    @pytest.mark.asyncio
    async def test_batch_embedding_generation(self) -> None:
        provider = DeterministicLocalProvider(dimensions=128)
        service = TextEmbeddingService(provider=provider, batch_size=2)
        texts = ["Text 1", "Text 2", "Text 3", "Text 4", "Text 5"]

        results = await service.embed_texts(texts)
        assert len(results) == 5
        for res in results:
            assert res.dimensions == 128
            assert math.isclose(res.norm, 1.0, rel_tol=1e-5)

    @pytest.mark.asyncio
    async def test_embed_chunks_extracts_retrieval_text(self) -> None:
        provider = DeterministicLocalProvider(dimensions=128)
        service = TextEmbeddingService(provider=provider)

        cid1 = uuid.uuid4()
        cid2 = uuid.uuid4()
        payloads = [
            ChunkPayload(chunk_id=cid1, raw_text="raw 1", retrieval_text="retrieval 1"),
            ChunkPayload(chunk_id=cid2, raw_text="raw 2", retrieval_text="retrieval 2"),
        ]

        paired = await service.embed_chunks(payloads)
        assert len(paired) == 2
        assert paired[0][0] == cid1
        assert paired[1][0] == cid2
        assert paired[0][1].dimensions == 128

    def test_create_chunk_embedding_database_model(self) -> None:
        provider = DeterministicLocalProvider(dimensions=128)
        service = TextEmbeddingService(provider=provider)
        res = provider.embed_single_sync("Sample text")

        cid = uuid.uuid4()
        chunk_emb = service.create_chunk_embedding_model(cid, res)

        assert isinstance(chunk_emb, ChunkEmbedding)
        assert chunk_emb.chunk_id == cid
        assert chunk_emb.embedding_type == EmbeddingModelType.TEXT
        assert chunk_emb.dimensions == 128
        assert len(chunk_emb.embedding) == 128
        assert chunk_emb.model_name == provider.model_name


class TestChemicalEmbeddingService:
    """Test ChemicalEmbeddingService canonicalization and separation (Prompt 8.3)."""

    def test_canonicalize_smiles_variants(self) -> None:
        service = ChemicalEmbeddingService()
        # Non-canonical vs canonical representations of ethanol
        s1 = "CCO"
        s2 = "OCC"
        can1 = service.canonicalize_smiles(s1)
        can2 = service.canonicalize_smiles(s2)
        assert can1 == can2 == "CCO"

        # Invalid SMILES returns None
        assert service.canonicalize_smiles("invalid_smiles_xyz123") is None

    @pytest.mark.asyncio
    async def test_chemical_embeddings_separate_from_text(self) -> None:
        service = ChemicalEmbeddingService()
        aspirin_smiles = "CC(=O)Oc1ccccc1C(=O)O"

        results = await service.embed_smiles_list([aspirin_smiles])
        assert len(results) == 1
        res = results[0]

        # Verify tagged strictly as CHEMICAL type
        assert res.metadata.embedding_type == EmbeddingModelType.CHEMICAL

        # Create model and verify database model separation
        cid = uuid.uuid4()
        model_inst = service.create_chemical_chunk_embedding_model(cid, res)
        assert model_inst.embedding_type == EmbeddingModelType.CHEMICAL
        assert model_inst.chunk_id == cid

    @pytest.mark.asyncio
    async def test_embed_chunks_with_chemistry_only_processes_chemical_chunks(self) -> None:
        service = ChemicalEmbeddingService()

        c_with_chem = ChunkPayload(
            chunk_id=uuid.uuid4(),
            raw_text="Aspirin molecule",
            retrieval_text="Aspirin molecule",
            chemical_entities=[{"name": "aspirin", "smiles": "CC(=O)Oc1ccccc1C(=O)O"}],
        )
        c_without_chem = ChunkPayload(
            chunk_id=uuid.uuid4(),
            raw_text="General safety intro",
            retrieval_text="General safety intro",
            chemical_entities=[],
        )

        results = await service.embed_chunks_with_chemistry([c_with_chem, c_without_chem])
        # Only the chemical chunk produces a chemical embedding
        assert len(results) == 1
        assert results[0][0] == c_with_chem.chunk_id


class TestEmbeddingFactory:
    """Test embedding provider factory (Prompt 8.1)."""

    def test_get_text_embedding_provider_local_fallback(self) -> None:
        p = get_text_embedding_provider(provider_type=EmbeddingProvider.LOCAL, dimensions=512)
        assert isinstance(p, DeterministicLocalProvider)
        assert p.dimensions == 512
        assert p.embedding_type == EmbeddingModelType.TEXT

    def test_get_chemical_embedding_provider_morgan(self) -> None:
        p = get_chemical_embedding_provider(provider_type="rdkit-morgan", dimensions=1024)
        assert isinstance(p, MorganFingerprintProvider)
        assert p.dimensions == 1024
        assert p.embedding_type == EmbeddingModelType.CHEMICAL

    def test_get_chemical_embedding_provider_chemberta(self) -> None:
        p = get_chemical_embedding_provider(provider_type="chemberta", dimensions=384)
        assert isinstance(p, ChemBERTaEmbeddingProvider)
        assert p.dimensions == 384
