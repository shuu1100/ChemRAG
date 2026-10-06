"""
Unit tests for Phase 10 — Reranking System.
Covers:
- Prompt 10.1: RerankerProvider interface and output schema.
- Prompt 10.2: Cross-Encoder candidate reranking and pool management.
- Prompt 10.3: ContextBuilder deduplication, token budgets, and provenance preservation.
- Exit Criteria: Deterministic context construction and retrieval quality improvement.
"""

from __future__ import annotations

import math
import uuid
import pytest

from backend.app.models.chunk import ChunkType
from backend.app.reranking.base import BaseRerankerProvider
from backend.app.reranking.context_builder import ContextBuilder, estimate_tokens
from backend.app.reranking.factory import get_reranker_provider
from backend.app.reranking.models import (
    AssembledContext,
    ContextBudget,
    RerankInputChunk,
    RerankResult,
)
from backend.app.reranking.providers.deterministic import (
    DeterministicRerankerProvider,
)
from backend.app.reranking.service import RerankingService
from backend.app.retrieval.models import ScoredChunk


class TestRerankerInterface:
    """Tests for Prompt 10.1 — Reranker Interface."""

    @pytest.mark.asyncio
    async def test_reranker_output_schema_and_metadata(self) -> None:
        provider = DeterministicRerankerProvider()
        cid1 = uuid.uuid4()
        cid2 = uuid.uuid4()

        chunks = [
            RerankInputChunk(chunk_id=cid1, text="Synthesis of aspirin acetylsalicylic acid", retrieval_score=0.5),
            RerankInputChunk(chunk_id=cid2, text="Random organic chemistry text", retrieval_score=0.4),
        ]

        results = await provider.rerank(
            query="aspirin synthesis",
            chunks=chunks,
            top_n=2,
        )

        assert len(results) == 2
        # Check output schema fields
        for res in results:
            assert isinstance(res, RerankResult)
            assert res.chunk_id in (cid1, cid2)
            assert 0.0 <= res.score <= 1.0
            assert res.rank in (1, 2)
            assert res.model_name == provider.model_name
            assert res.latency_ms >= 0.0

        # Most relevant chunk should rank 1
        assert results[0].chunk_id == cid1
        assert results[0].rank == 1

    def test_factory_returns_provider(self) -> None:
        p = get_reranker_provider(provider_type="local")
        assert isinstance(p, DeterministicRerankerProvider)


class TestRerankingService:
    """Tests for Prompt 10.2 — Cross-Encoder Service."""

    @pytest.mark.asyncio
    async def test_service_reranks_and_reorders_candidates(self) -> None:
        service = RerankingService(provider=DeterministicRerankerProvider())

        cid_target = uuid.uuid4()
        cid_distractor = uuid.uuid4()

        # Distractor initially ranks 1 based on upstream RRF score
        distractor_chunk = ScoredChunk(
            chunk_id=cid_distractor,
            document_id=uuid.uuid4(),
            content="General chemical laboratory glassware maintenance protocol",
            retrieval_text="General chemical laboratory glassware maintenance protocol",
            score=0.9,
            rank=1,
            retrieval_mode="hybrid_rrf",
        )
        target_chunk = ScoredChunk(
            chunk_id=cid_target,
            document_id=uuid.uuid4(),
            content="Exact procedure for synthesizing aspirin with acetic anhydride and H3PO4",
            retrieval_text="Exact procedure for synthesizing aspirin with acetic anhydride and H3PO4",
            score=0.4,
            rank=2,
            retrieval_mode="hybrid_rrf",
        )

        reranked = await service.rerank_candidates(
            query="procedure for synthesizing aspirin with acetic anhydride",
            candidates=[distractor_chunk, target_chunk],
            top_n=2,
            pool_size=10,
        )

        assert len(reranked) == 2
        # Cross-encoder promotes relevant target chunk to Rank 1
        assert reranked[0].chunk_id == cid_target
        assert reranked[0].rank == 1
        assert reranked[0].score_breakdown["pre_rerank_rank"] == 2
        assert "reranker_score" in reranked[0].score_breakdown
        assert reranked[0].retrieval_mode == "cross_encoder_reranked"


class TestContextBuilder:
    """Tests for Prompt 10.3 — Context Builder."""

    def test_deduplication_removes_identical_content(self) -> None:
        builder = ContextBuilder()
        cid1 = uuid.uuid4()
        cid2 = uuid.uuid4()

        # Identical text in two separate chunks
        chunk1 = ScoredChunk(
            chunk_id=cid1,
            document_id=uuid.uuid4(),
            content="Repeated protocol paragraph across sections",
            score=0.95,
            rank=1,
        )
        chunk2 = ScoredChunk(
            chunk_id=cid2,
            document_id=uuid.uuid4(),
            content="Repeated protocol paragraph across sections",
            score=0.80,
            rank=2,
        )

        context = builder.build_context([chunk1, chunk2])
        # Duplicate must be filtered out
        assert context.chunks_used_count == 1
        assert len(context.citations) == 1
        assert context.citations[0].chunk_id == cid1

    def test_token_budget_enforcement_and_dropping(self) -> None:
        # Strict low budget: 50 context tokens
        small_budget = ContextBudget(max_tokens=200, reserve_for_answer=150, max_chunks=5)
        builder = ContextBuilder(budget=small_budget)

        chunks = [
            ScoredChunk(
                chunk_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                content="Short snippet that fits in budget easily." * 2,
                score=0.9,
                rank=1,
            ),
            ScoredChunk(
                chunk_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                content="A second snippet that will exceed the remaining token budget." * 10,
                score=0.8,
                rank=2,
            ),
        ]

        context = builder.build_context(chunks, budget=small_budget)
        assert context.chunks_used_count == 1
        assert context.chunks_dropped_count >= 1
        assert context.total_tokens <= small_budget.max_context_tokens

    def test_preserves_provenance_tables_and_equations(self) -> None:
        builder = ContextBuilder()
        cid = uuid.uuid4()
        did = uuid.uuid4()

        chunk_table = ScoredChunk(
            chunk_id=cid,
            document_id=did,
            content="[Table 1: Yields] | Solvent | Temp | Yield |",
            chunk_type=ChunkType.TABLE,
            page_number=3,
            score=0.9,
            metadata={"document_title": "Synthesis Paper", "section_title": "Results", "bbox": {"x0": 10, "y0": 20, "x1": 100, "y1": 200}},
        )

        context = builder.build_context([chunk_table])
        assert context.chunks_used_count == 1
        assert context.preserved_elements["tables"] >= 1

        citation = context.citations[0]
        assert citation.chunk_id == cid
        assert citation.document_id == did
        assert citation.title == "Synthesis Paper"
        assert citation.page_number == 3
        assert citation.section_title == "Results"
        assert citation.bbox == {"x0": 10, "y0": 20, "x1": 100, "y1": 200}
        assert "[1]" in context.context_text

    def test_context_construction_is_deterministic(self) -> None:
        builder = ContextBuilder()
        chunks = [
            ScoredChunk(chunk_id=uuid.uuid4(), document_id=uuid.uuid4(), content="First chunk content", score=0.9, rank=1),
            ScoredChunk(chunk_id=uuid.uuid4(), document_id=uuid.uuid4(), content="Second chunk content", score=0.8, rank=2),
        ]

        ctx1 = builder.build_context(chunks)
        ctx2 = builder.build_context(chunks)

        assert ctx1.context_text == ctx2.context_text
        assert ctx1.total_tokens == ctx2.total_tokens
        assert [c.citation_id for c in ctx1.citations] == [c.citation_id for c in ctx2.citations]
