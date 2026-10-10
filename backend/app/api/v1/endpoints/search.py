"""
ChemRAG — Search & Retrieval Endpoints
======================================
Covers:
- POST /search         (Hybrid semantic, lexical, chemical retrieval + cross-encoder reranking)
- POST /search/hybrid  (Alias endpoint for hybrid search)
- GET  /search/diagnostics (System retrieval diagnostics)
"""

from __future__ import annotations

import time
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.models.chunk import Chunk, ChunkEmbedding
from backend.app.models.document import Document
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
@router.post(
    "/hybrid",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute hybrid search (alias route)",
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

    query_str = request.get_query_str()
    if not query_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty.",
        )

    hybrid_service = HybridRetrievalService()
    reranker_service = RerankingService()
    context_builder = ContextBuilder()

    payload = RetrievalQueryPayload(
        query_text=query_str,
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
            query=query_str,
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
            query=query_str,
        )

    latency_ms = (time.perf_counter() - t0) * 1000.0

    return SearchResponse(
        query_text=query_str,
        query_smiles=request.query_smiles,
        total_results=len(final_results),
        results=final_results,
        context=assembled_ctx,
        latency_ms=round(latency_ms, 2),
    )


@router.get(
    "/diagnostics",
    summary="Get retrieval diagnostics and index statistics",
)
async def get_search_diagnostics(
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Returns retrieval system health, indexed document count, chunk count, and embedding status.
    """
    pgvector_active = False
    try:
        pgv_res = await session.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector';"))
        pgvector_active = pgv_res.scalar_one_or_none() is not None
    except Exception:
        pgvector_active = False

    doc_cnt = (await session.execute(select(func.count(Document.id)).where(Document.deleted_at.is_(None)))).scalar_one_or_none() or 0
    chunk_cnt = (await session.execute(select(func.count(Chunk.id)).where(Chunk.is_current.is_(True)))).scalar_one_or_none() or 0
    emb_cnt = (await session.execute(select(func.count(ChunkEmbedding.id)))).scalar_one_or_none() or 0

    return {
        "status": "healthy",
        "pgvector_active": pgvector_active,
        "indexed_documents_count": doc_cnt,
        "indexed_chunks_count": chunk_cnt,
        "stored_embeddings_count": emb_cnt,
        "lexical_retriever": "PostgreSQLLexicalRetriever (ts_rank_cd)",
        "semantic_retriever": "SemanticRetriever (pgvector 3072d HNSW)",
        "hybrid_fusion": "ReciprocalRankFusion (k=60)",
        "reranker": "RerankingService (Cohere / Cross-Encoder)",
    }
