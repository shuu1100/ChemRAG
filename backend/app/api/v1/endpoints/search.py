"""
ChemRAG — Search & Retrieval Endpoints
======================================
Covers:
- POST /search  (Hybrid semantic, lexical, chemical retrieval + cross-encoder reranking + context builder)
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.reranking.context_builder import ContextBuilder
from backend.app.reranking.service import RerankingService
from backend.app.retrieval.hybrid import HybridRetrievalService
from backend.app.retrieval.models import RetrievalQueryPayload
from backend.app.schemas.retrieval import SearchRequest, SearchResponse

router = APIRouter()


@router.post(
    "",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute hybrid search and cross-encoder reranking",
)
async def search_documents(
    request: SearchRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SearchResponse:
    """
    Execute multi-modal hybrid retrieval:
    1. Dense semantic vector retrieval via pgvector HNSW
    2. Full-text search via PostgreSQL tsvector and exact trigram technical identifiers
    3. Chemical molecular identity and similarity retrieval
    4. Reciprocal Rank Fusion (RRF)
    5. Optional Cross-Encoder reranking
    6. Optional Prompt context assembly preserving citation provenance
    """
    t0 = time.perf_counter()

    hybrid_service = HybridRetrievalService()
    reranker_service = RerankingService()
    context_builder = ContextBuilder()

    payload = RetrievalQueryPayload(
        query_text=request.query_text,
        query_smiles=request.query_smiles,
        top_k=request.top_k if not request.rerank else max(request.top_k, request.rerank_pool_size),
        filters=request.filters,
    )

    # 1. Retrieve candidates via hybrid RRF
    raw_results = await hybrid_service.search(
        payload=payload,
        session=session,
        log_query=True,
    )

    # 2. Cross-encoder reranking
    final_results = raw_results
    if request.rerank and raw_results:
        final_results = await reranker_service.rerank_candidates(
            query=request.query_text,
            candidates=raw_results,
            top_n=request.top_k,
            pool_size=request.rerank_pool_size,
        )
    else:
        final_results = raw_results[:request.top_k]

    # 3. Optional Context Construction
    assembled_ctx = None
    if request.build_context and final_results:
        assembled_ctx = context_builder.build_context(
            chunks=final_results,
            query=request.query_text,
        )

    latency_ms = (time.perf_counter() - t0) * 1000.0

    return SearchResponse(
        query_text=request.query_text,
        query_smiles=request.query_smiles,
        total_results=len(final_results),
        results=final_results,
        context=assembled_ctx,
        latency_ms=round(latency_ms, 2),
    )
