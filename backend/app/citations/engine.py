"""
ChemRAG — Citation Engine
==========================
Fulfills Prompt 13.1:
- Assigns stable, deterministic citation identifiers (e.g., [CIT-001]) to evidence chunks.
- Binds each citation ID to chunk ID, document, version, page number, section, and bounding box.
- Assembles LLM prompt context with explicit citation headers so the LLM uses valid citation IDs.
- Prevents LLM from inventing or hallucinating reference data.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple
import uuid

from backend.app.citations.models import CitationMetadata
from backend.app.reranking.models import AssembledCitation, RerankResult
from backend.app.retrieval.models import ScoredChunk

logger = logging.getLogger(__name__)


class CitationEngine:
    """
    Manages stable citation assignment, lookup, and context formatting for scientific evidence.
    """

    def __init__(self, id_prefix: str = "CIT-") -> None:
        self.id_prefix = id_prefix

    def format_citation_id(self, index: int) -> str:
        """Generate formatted citation string, e.g. CIT-001 or [CIT-001]."""
        return f"{self.id_prefix}{index:03d}"

    def assign_citations(
        self, chunks: Sequence[RerankResult | ScoredChunk]
    ) -> List[CitationMetadata]:
        """
        Assign stable CIT-xxx identifiers to a list of retrieved/reranked evidence chunks.
        """
        citations: List[CitationMetadata] = []

        for idx, chunk in enumerate(chunks, start=1):
            cit_id = self.format_citation_id(idx)

            if isinstance(chunk, RerankResult):
                cid = chunk.chunk_id
                did = chunk.document_id
                page = chunk.page_number
                section = chunk.section_title
                text_snippet = chunk.text
                meta = chunk.metadata if isinstance(chunk.metadata, dict) else {}
                bbox = meta.get("bbox")
                doc_title = meta.get("document_title") or "Scientific Document"
                conf = chunk.score
                doi = meta.get("doi")
            else:
                cid = chunk.chunk_id
                did = chunk.document_id
                page = chunk.page_number
                meta = chunk.metadata if isinstance(chunk.metadata, dict) else {}
                section = meta.get("section_title")
                text_snippet = chunk.display_text or chunk.retrieval_text or chunk.content
                bbox = chunk.bbox or meta.get("bbox")
                doc_title = meta.get("document_title") or "Scientific Document"
                conf = chunk.score
                doi = meta.get("doi")

            cit = CitationMetadata(
                citation_id=cit_id,
                chunk_id=cid,
                document_id=did,
                document_title=doc_title,
                page_number=page,
                section_title=section,
                bbox=bbox,
                confidence=round(conf, 4),
                raw_text=text_snippet.strip(),
                doi=doi,
                extra_metadata=meta,
            )
            citations.append(cit)

        return citations

    def format_context_with_citations(
        self, citations: List[CitationMetadata]
    ) -> str:
        """
        Format evidence blocks with explicit citation headers for LLM input prompt.
        Format:
        ### Evidence [{cit.citation_id}] | Document: {cit.document_title} | Page: {cit.page_number}
        {cit.raw_text}
        """
        blocks: List[str] = []
        for cit in citations:
            header_parts = [f"[{cit.citation_id}] {cit.document_title}"]
            if cit.section_title:
                header_parts.append(f"Section: {cit.section_title}")
            if cit.page_number is not None:
                header_parts.append(f"Page: {cit.page_number}")
            if cit.doi:
                header_parts.append(f"DOI: {cit.doi}")

            header_str = " | ".join(header_parts)
            block = f"### Evidence {header_str}\n{cit.raw_text}\n"
            blocks.append(block)

        return "\n".join(blocks)

    def resolve_citation(
        self, citation_id: str, citations: List[CitationMetadata]
    ) -> Optional[CitationMetadata]:
        """
        Find CitationMetadata matching citation_id (accepts 'CIT-001' or '[CIT-001]').
        """
        clean_id = citation_id.strip("[] ").upper()
        for cit in citations:
            if cit.citation_id.upper() == clean_id:
                return cit
        return None
