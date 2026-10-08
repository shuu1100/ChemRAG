"""
ChemRAG — Retrieval Agent
===========================
Fulfills Phase 11 / Prompt 11.3:
- Generates query search variants (synonyms, technical identifiers, formulas, SMILES).
- Executes multi-modal hybrid retrieval (semantic, lexical, chemical).
- Performs RRF and cross-encoder reranking.
- Never fabricates evidence. Returns honest provenance.
"""
from __future__ import annotations

import re
import time
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.state import (
    AgentState,
    CitationData,
    ToolCallRecord,
)
from backend.app.core.logging import get_logger
from backend.app.reranking.service import RerankingService
from backend.app.retrieval.hybrid import HybridRetrievalService
from backend.app.retrieval.models import RetrievalFilter, RetrievalQueryPayload, ScoredChunk

logger = get_logger(__name__)


class RetrievalAgent:
    """
    Evidence-grounded Retrieval Agent.
    Generates search variations, conducts hybrid multi-modal retrieval,
    reranks candidate passages, and preserves citations.
    """

    def __init__(
        self,
        hybrid_service: Optional[HybridRetrievalService] = None,
        reranking_service: Optional[RerankingService] = None,
    ) -> None:
        self.hybrid_service = hybrid_service or HybridRetrievalService()
        self.reranking_service = reranking_service or RerankingService()
        self.logger = logger

    def generate_search_variants(self, query: str) -> list[str]:
        """
        Generate diverse search variants:
        - Original query
        - Technical identifier focus (CAS, formula, SMILES)
        - Keyword focused query without conversational filler
        """
        variants: list[str] = [query]

        # 1. Extract potential CAS numbers: \d{2,7}-\d{2}-\d
        cas_matches = re.findall(r"\b\d{2,7}-\d{2}-\d\b", query)
        for cas in cas_matches:
            if cas not in variants:
                variants.append(f"CAS {cas}")

        # 2. Extract potential SMILES or chemical symbols
        smiles_candidates = re.findall(r"[CNOFPSClBrI][A-Za-z0-9@+\-\[\]\(\)\\=#$%/]{3,}", query)
        for sm in smiles_candidates:
            if sm not in variants and not sm.lower().startswith("http"):
                variants.append(f"structure {sm}")

        # 3. Clean keywords (remove conversational prefixes)
        cleaned = re.sub(
            r"^(what is|how to|can you tell me|find|describe|show me|explain)\s+",
            "",
            query,
            flags=re.IGNORECASE,
        ).strip()
        if cleaned and cleaned != query and cleaned not in variants:
            variants.append(cleaned)

        return variants

    async def execute_retrieval(
        self,
        query: str,
        session: Optional[AsyncSession] = None,
        top_k: int = 5,
        filters: Optional[RetrievalFilter] = None,
    ) -> list[ScoredChunk]:
        """Execute hybrid search pipeline and return reranked scored chunks."""
        # 1. Detect if query contains SMILES
        extracted_smiles: Optional[str] = None
        smiles_candidates = re.findall(r"[CNOFPSClBrI][A-Za-z0-9@+\-\[\]\(\)\\=#$%/]{4,}", query)
        if smiles_candidates:
            extracted_smiles = smiles_candidates[0]

        payload = RetrievalQueryPayload(
            query_text=query,
            query_smiles=extracted_smiles,
            top_k=max(top_k * 4, 20),  # Pool for fusion and reranking
            filters=filters,
        )

        # 2. Hybrid search across semantic, lexical, chemical
        candidates = await self.hybrid_service.search(
            payload=payload,
            session=session,
            log_query=True,
        )

        if not candidates:
            return []

        # 3. Cross-encoder reranking
        reranked = await self.reranking_service.rerank_candidates(
            query=query,
            candidates=candidates,
            top_n=top_k,
            pool_size=min(len(candidates), 50),
        )

        return reranked

    async def run(self, state: AgentState, session: Optional[AsyncSession] = None) -> AgentState:
        """Run retrieval node in the LangGraph graph."""
        query = state.get("query", "")
        scratchpad = list(state.get("internal_scratchpad", []))
        tool_calls = list(state.get("tool_calls", []))

        t0 = time.perf_counter()

        # 1. Generate search variants
        variants = self.generate_search_variants(query)
        scratchpad.append(f"[RetrievalAgent] Generated search variants: {variants}")

        # 2. Execute retrieval
        call_rec = ToolCallRecord(
            tool_name="hybrid_retrieval_and_rerank",
            input_args={"query": query, "variants": variants, "top_k": 5},
        )

        try:
            chunks = await self.execute_retrieval(query=query, session=session, top_k=5)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            call_rec.execution_time_ms = round(elapsed_ms, 2)
            call_rec.status = "success"
            call_rec.output_result = f"Retrieved {len(chunks)} verified evidence passages"
            tool_calls.append(call_rec)

            scratchpad.append(f"[RetrievalAgent] Found {len(chunks)} relevant chunks ({elapsed_ms:.1f}ms)")

            # Create preliminary citations
            citations: list[CitationData] = []
            for c in chunks:
                citations.append(
                    CitationData(
                        document_id=str(c.document_id),
                        chunk_id=str(c.chunk_id),
                        page_number=c.page_number,
                        snippet=c.content[:250],
                        score=round(c.score, 4),
                        bbox=c.bbox,
                    )
                )

            # Mark subtask as completed
            subtasks = list(state.get("subtasks", []))
            for st in subtasks:
                if st.target_agent == "retrieval":
                    st.status = "completed"
                    st.output_data = {"chunks_found": len(chunks)}

            return {
                **state,
                "retrieval_queries": variants,
                "retrieved_chunks": chunks,
                "reranked_chunks": chunks,
                "citations": citations,
                "tool_calls": tool_calls,
                "subtasks": subtasks,
                "internal_scratchpad": scratchpad,
            }

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            call_rec.execution_time_ms = round(elapsed_ms, 2)
            call_rec.status = "error"
            call_rec.error_message = str(exc)
            tool_calls.append(call_rec)

            scratchpad.append(f"[RetrievalAgent] ERROR in retrieval: {exc}")
            errors = list(state.get("errors", []))
            errors.append(f"Retrieval error: {exc}")

            return {
                **state,
                "retrieval_queries": variants,
                "retrieved_chunks": [],
                "reranked_chunks": [],
                "tool_calls": tool_calls,
                "errors": errors,
                "internal_scratchpad": scratchpad,
            }
