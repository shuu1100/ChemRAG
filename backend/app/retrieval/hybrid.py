"""
Hybrid Retrieval Orchestrator Service.
Coordinates Semantic, Lexical, and Chemical retrievers with RRF fusion.
Provides comprehensive audit logging to RetrievalQuery and RetrievalResult models.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Sequence
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.pipeline import RetrievalQuery, RetrievalResult
from backend.app.retrieval.chemical import ChemicalRetriever
from backend.app.retrieval.fusion import ReciprocalRankFusion
from backend.app.retrieval.lexical import BaseLexicalRetriever, PostgreSQLLexicalRetriever
from backend.app.retrieval.models import RetrievalFilter, RetrievalQueryPayload, ScoredChunk
from backend.app.retrieval.semantic import SemanticRetriever

logger = logging.getLogger(__name__)


class HybridRetrievalService:
    """
    Main retrieval orchestrator for ChemRAG.
    Executes multi-modal retrieval across semantic, lexical, and chemical dimensions
    and fuses candidates using Reciprocal Rank Fusion.
    """

    def __init__(
        self,
        semantic_retriever: SemanticRetriever | None = None,
        lexical_retriever: BaseLexicalRetriever | None = None,
        chemical_retriever: ChemicalRetriever | None = None,
        rrf_fusion: ReciprocalRankFusion | None = None,
    ) -> None:
        self.semantic = semantic_retriever or SemanticRetriever()
        self.lexical = lexical_retriever or PostgreSQLLexicalRetriever()
        self.chemical = chemical_retriever or ChemicalRetriever()
        self.fusion = rrf_fusion or ReciprocalRankFusion()

    async def search(
        self,
        payload: RetrievalQueryPayload,
        session: AsyncSession,
        log_query: bool = False,
        user_id: uuid.UUID | None = None,
    ) -> list[ScoredChunk]:
        """
        Execute unified hybrid search:
        1. Semantic retrieval (pgvector cosine)
        2. Lexical retrieval (tsvector + trigram technical identifier)
        3. Chemical retrieval (InChIKey / formula / molecular similarity)
        4. Reciprocal Rank Fusion (RRF)
        """
        t0 = time.perf_counter()
        multimodal_results: dict[str, list[ScoredChunk]] = {}

        # 1. Semantic search
        if payload.semantic_weight > 0.0 and payload.query_text:
            sem_chunks = await self.semantic.search(
                query_text=payload.query_text,
                session=session,
                top_k=payload.top_k * 2,  # Oversample for fusion
                filters=payload.filters,
                ef_search=payload.ef_search,
            )
            multimodal_results["semantic"] = sem_chunks

        # 2. Lexical search
        if payload.lexical_weight > 0.0 and payload.query_text:
            lex_chunks = await self.lexical.search(
                query_text=payload.query_text,
                session=session,
                top_k=payload.top_k * 2,
                filters=payload.filters,
            )
            multimodal_results["lexical"] = lex_chunks

        # 3. Chemical search
        if payload.chemical_weight > 0.0 and (payload.query_smiles or payload.query_text):
            chem_chunks = await self.chemical.search(
                query=payload.query_text,
                session=session,
                query_smiles=payload.query_smiles,
                top_k=payload.top_k * 2,
                filters=payload.filters,
            )
            if chem_chunks:
                multimodal_results["chemical"] = chem_chunks

        # 4. RRF Fusion
        fusion_engine = ReciprocalRankFusion(
            k=payload.rrf_k,
            weights={
                "semantic": payload.semantic_weight,
                "lexical": payload.lexical_weight,
                "chemical": payload.chemical_weight,
            },
        )
        final_results = fusion_engine.fuse(
            retrieval_results=multimodal_results,
            top_k=payload.top_k,
        )

        latency_ms = (time.perf_counter() - t0) * 1000.0

        # 5. Optional query logging for lineage and evaluation
        if log_query and payload.filters and payload.filters.organization_id:
            try:
                rq = RetrievalQuery(
                    organization_id=payload.filters.organization_id,
                    user_id=user_id,
                    query_text=payload.query_text,
                    top_k=payload.top_k,
                    retrieval_strategy="hybrid_rrf",
                    execution_time_ms=latency_ms,
                    results_count=len(final_results),
                )
                session.add(rq)
                await session.flush()

                for sc in final_results:
                    rr = RetrievalResult(
                        query_id=rq.id,
                        chunk_id=sc.chunk_id,
                        rank=sc.rank,
                        score=sc.score,
                        score_breakdown=sc.score_breakdown,
                        retrieval_strategy="hybrid_rrf",
                    )
                    session.add(rr)
                await session.commit()
            except Exception as log_exc:
                logger.warning("Could not persist retrieval query audit record: %s", log_exc)

        return final_results
