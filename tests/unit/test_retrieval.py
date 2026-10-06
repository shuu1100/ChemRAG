"""
Unit tests for Phase 09 — Hybrid Retrieval.
Covers:
- Prompt 9.1: Semantic retriever with pgvector cosine similarity and filters.
- Prompt 9.2: Lexical retriever with tsvector, ts_rank_cd, and exact technical identifier search.
- Prompt 9.3: Chemical retriever distinguishing identity, molecular similarity, and formulas.
- Prompt 9.4: Reciprocal Rank Fusion (RRF) with component ranks and deterministic ordering.
- Prompt 9.5: Filtered ANN selectivity measurement.
"""

from __future__ import annotations

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.app.embeddings.providers.deterministic import DeterministicLocalProvider
from backend.app.embeddings.providers.morgan import MorganFingerprintProvider
from backend.app.models.chunk import Chunk, ChunkEmbedding, ChunkType, EmbeddingModelType
from backend.app.models.document import Document
from backend.app.retrieval.chemical import ChemicalRetriever
from backend.app.retrieval.filtered_ann import FilteredANNScanner, ScanOrderMode
from backend.app.retrieval.fusion import ReciprocalRankFusion
from backend.app.retrieval.hybrid import HybridRetrievalService
from backend.app.retrieval.lexical import PostgreSQLLexicalRetriever
from backend.app.retrieval.models import (
    RetrievalFilter,
    RetrievalQueryPayload,
    ScoredChunk,
)
from backend.app.retrieval.semantic import SemanticRetriever


class TestSemanticRetriever:
    """Tests for Prompt 9.1 — Semantic Retriever."""

    @pytest.mark.asyncio
    async def test_semantic_retrieval_computes_cosine_and_filters(self) -> None:
        provider = DeterministicLocalProvider(dimensions=128)
        retriever = SemanticRetriever(embedding_provider=provider)

        cid1 = uuid.uuid4()
        cid2 = uuid.uuid4()
        doc_id = uuid.uuid4()
        org_id = uuid.uuid4()

        c1 = Chunk(id=cid1, document_id=doc_id, content="Benzene catalytic hydrogenation", is_current=True)
        c2 = Chunk(id=cid2, document_id=doc_id, content="Aspirin synthesis procedure", is_current=True)
        d = Document(id=doc_id, organization_id=org_id)

        v1 = (await provider.embed_single("Benzene catalytic hydrogenation")).vector
        v2 = (await provider.embed_single("Aspirin synthesis procedure")).vector

        ce1 = ChunkEmbedding(chunk_id=cid1, embedding=v1, dimensions=128, model_name=provider.model_name, embedding_type=EmbeddingModelType.TEXT)
        ce2 = ChunkEmbedding(chunk_id=cid2, embedding=v2, dimensions=128, model_name=provider.model_name, embedding_type=EmbeddingModelType.TEXT)

        # Mock database session returning chunks
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [(c1, ce1), (c2, ce2)]
        mock_session.execute.return_value = mock_result

        results = await retriever._in_memory_search(
            query_text="benzene hydrogenation",
            session=mock_session,
            top_k=2,
            filters=RetrievalFilter(organization_id=org_id),
            query_vec=(await provider.embed_single("benzene hydrogenation")).vector,
        )

        assert len(results) == 2
        assert results[0].chunk_id == cid1
        assert results[0].score > results[1].score
        assert results[0].score_breakdown["semantic_rank"] == 1
        assert results[0].retrieval_mode == "semantic"


class TestLexicalRetriever:
    """Tests for Prompt 9.2 — Lexical Retriever."""

    def test_extract_technical_identifiers(self) -> None:
        retriever = PostgreSQLLexicalRetriever()
        query = "Find safety data for CAS 50-78-2 and equipment REACT-102"
        identifiers = retriever.extract_technical_identifiers(query)
        assert "50-78-2" in identifiers
        assert "REACT-102" in identifiers

    @pytest.mark.asyncio
    async def test_lexical_retrieval_matches_and_ranks_exact_identifier(self) -> None:
        retriever = PostgreSQLLexicalRetriever()

        cid1 = uuid.uuid4()
        cid2 = uuid.uuid4()
        doc_id = uuid.uuid4()

        c1 = Chunk(id=cid1, document_id=doc_id, content="Aspirin CAS 50-78-2 is acetylsalicylic acid", is_current=True)
        c2 = Chunk(id=cid2, document_id=doc_id, content="Paracetamol CAS 103-90-2 is acetaminophen", is_current=True)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [c1, c2]
        mock_session.execute.return_value = mock_result

        results = await retriever._in_memory_search(
            query="CAS 50-78-2 aspirin",
            session=mock_session,
            top_k=2,
            filters=None,
            technical_ids=["50-78-2"],
        )

        assert len(results) >= 1
        # Chunk with exact CAS 50-78-2 must rank first
        assert results[0].chunk_id == cid1
        assert results[0].score_breakdown["lexical_rank"] == 1
        assert results[0].retrieval_mode == "lexical"


class TestChemicalRetriever:
    """Tests for Prompt 9.3 — Chemical Retriever."""

    def test_distinguishes_identity_and_smiles_canonicalization(self) -> None:
        retriever = ChemicalRetriever()
        canonical = retriever.canonicalize("OCC")
        assert canonical == "CCO"

        inchikey = retriever.smiles_to_inchikey("CCO")
        assert inchikey is not None
        assert len(inchikey) == 27
        assert "-" in inchikey

    @pytest.mark.asyncio
    async def test_chemical_retrieval_returns_exact_identity_score_1(self) -> None:
        retriever = ChemicalRetriever()
        cid = uuid.uuid4()
        doc_id = uuid.uuid4()
        c = Chunk(id=cid, document_id=doc_id, content="Salicylic acid sample", is_current=True)

        chem_entity = MagicMock()
        chem_entity.common_name = "Salicylic acid"
        chem_entity.iupac_name = "2-hydroxybenzoic acid"
        chem_entity.inchi_key = "YGSDEFSMJLZEOE-UHFFFAOYSA-N"
        chem_entity.canonical_smiles = "O=C(O)c1ccccc1O"
        chem_entity.cas_number = "69-72-7"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [(c, chem_entity)]
        mock_session.execute.return_value = mock_result

        results = await retriever._search_exact_identity(
            session=mock_session,
            target_inchikey="YGSDEFSMJLZEOE-UHFFFAOYSA-N",
            target_smiles="O=C(O)c1ccccc1O",
            query_text="69-72-7",
            filters=None,
        )

        assert len(results) == 1
        assert results[0].score == 1.0  # Exact identity match must be 1.0
        assert results[0].score_breakdown["match_type"] == "exact_identity"


class TestReciprocalRankFusion:
    """Tests for Prompt 9.4 — RRF."""

    def test_rrf_combines_ranks_deterministically(self) -> None:
        fusion = ReciprocalRankFusion(k=60)

        cid1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
        cid2 = uuid.UUID("22222222-2222-2222-2222-222222222222")
        cid3 = uuid.UUID("33333333-3333-3333-3333-333333333333")
        doc_id = uuid.uuid4()

        # Semantic ranks: cid1=1, cid2=2
        sem_chunks = [
            ScoredChunk(chunk_id=cid1, document_id=doc_id, content="Chunk 1", score=0.9, rank=1, retrieval_mode="semantic"),
            ScoredChunk(chunk_id=cid2, document_id=doc_id, content="Chunk 2", score=0.8, rank=2, retrieval_mode="semantic"),
        ]
        # Lexical ranks: cid2=1, cid3=2
        lex_chunks = [
            ScoredChunk(chunk_id=cid2, document_id=doc_id, content="Chunk 2", score=5.0, rank=1, retrieval_mode="lexical"),
            ScoredChunk(chunk_id=cid3, document_id=doc_id, content="Chunk 3", score=3.0, rank=2, retrieval_mode="lexical"),
        ]

        fused = fusion.fuse({"semantic": sem_chunks, "lexical": lex_chunks}, top_k=3)

        assert len(fused) == 3
        # cid2 appears in both lists: (1/(60+2)) + (1/(60+1)) = 1/62 + 1/61 ~ 0.0161 + 0.0163 = 0.0325
        # cid1 appears in only sem: 1/61 ~ 0.0163
        # cid3 appears in only lex: 1/62 ~ 0.0161
        # Therefore cid2 must rank first!
        assert fused[0].chunk_id == cid2
        assert fused[0].rank == 1
        assert fused[0].score_breakdown["semantic_rank"] == 2
        assert fused[0].score_breakdown["lexical_rank"] == 1
        assert fused[0].retrieval_mode == "hybrid_rrf"

    def test_rrf_empty_inputs_returns_empty(self) -> None:
        fusion = ReciprocalRankFusion()
        assert fusion.fuse({}) == []


class TestFilteredANN:
    """Tests for Prompt 9.5 — Filtered ANN."""

    def test_filtered_ann_measures_selectivity_drop(self) -> None:
        scanner = FilteredANNScanner()
        corpus_size = 100
        # Create vectors where target items have high similarity
        vectors = [[0.1] * 16 for _ in range(corpus_size)]
        # Target tag for only 2 items (2% selectivity)
        tags = ["rare_tag" if i < 2 else "common_tag" for i in range(corpus_size)]
        query_vec = [0.1] * 16

        res = scanner.benchmark_filter_selectivity(
            corpus_vectors=vectors,
            corpus_tags=tags,
            query_vector=query_vec,
            target_tag="rare_tag",
            top_k=2,
            ef_search=10,
        )

        assert res["matching_items_count"] == 2
        assert res["selectivity_percent"] == 2.0
        assert "pre_filter_recall" in res
        assert "post_filter_recall" in res
        assert "recall_delta" in res


class TestHybridRetrievalService:
    """Integration test for HybridRetrievalService."""

    @pytest.mark.asyncio
    async def test_hybrid_search_orchestration(self) -> None:
        service = HybridRetrievalService()
        mock_session = AsyncMock()

        # Mock semantic and lexical returning dummy ScoredChunk
        cid = uuid.uuid4()
        dummy_chunk = ScoredChunk(
            chunk_id=cid,
            document_id=uuid.uuid4(),
            content="Sample hybrid result",
            score=0.85,
            rank=1,
            retrieval_mode="semantic",
        )
        service.semantic.search = AsyncMock(return_value=[dummy_chunk])
        service.lexical.search = AsyncMock(return_value=[dummy_chunk])
        service.chemical.search = AsyncMock(return_value=[])

        payload = RetrievalQueryPayload(
            query_text="aspirin synthesis",
            top_k=5,
        )
        results = await service.search(payload, mock_session)

        assert len(results) == 1
        assert results[0].chunk_id == cid
        assert results[0].retrieval_mode == "hybrid_rrf"
        assert "rrf_score" in results[0].score_breakdown
