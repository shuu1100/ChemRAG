"""
Context Builder for LLM Prompt Assembly.
Fulfills Prompt 10.3:
- Deduplicates chunks without loss of meaning.
- Preserves document hierarchy, page numbers, and spatial provenance.
- Preserves equations, chemical structures (SMILES/InChI), and table row context.
- Enforces strict token budgets and prioritizes high-confidence evidence.
- Never discards citation metadata.
- Fully deterministic context construction.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Sequence
import uuid

from backend.app.models.chunk import ChunkType
from backend.app.reranking.models import (
    AssembledCitation,
    AssembledContext,
    ContextBudget,
    RerankResult,
)
from backend.app.retrieval.models import ScoredChunk

logger = logging.getLogger(__name__)

# Patterns for chemical, equation, and tabular markers
SMILES_OR_INCHI_PATTERN = re.compile(r"\b(?:InChI=1S/|InChIKey=|[A-Z][a-z0-9#=\(\)\[\]\+\-\\\/@]+)\b")
EQUATION_PATTERN = re.compile(r"(\$\$.*?\$\$|\\\[.*?\\\]|\$.*?\$|\\Delta|\\ln|\\frac)")
TABLE_PATTERN = re.compile(r"(\|.*?\||\[Table\s+\d+:)")


def estimate_tokens(text: str) -> int:
    """
    Robust whitespace + punctuation token estimation (approx 1 token ~ 4 chars or 0.75 words).
    """
    if not text:
        return 0
    words = len(text.split())
    chars = len(text)
    # Hybrid token estimation calibrated for technical scientific text
    return max(1, int(max(words * 1.3, chars / 3.8)))


class ContextBuilder:
    """
    Assembles evidence chunks into structured, provenance-preserving context prompts.
    """

    def __init__(self, budget: ContextBudget | None = None) -> None:
        self.budget = budget or ContextBudget()

    def _content_hash(self, text: str) -> str:
        """Normalized content hash for deduplication."""
        normalized = re.sub(r"\s+", " ", text.strip().lower())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def build_context(
        self,
        chunks: Sequence[RerankResult | ScoredChunk],
        query: str = "",
        budget: ContextBudget | None = None,
    ) -> AssembledContext:
        """
        Assemble final context within token budget while preserving citations and chemistry.
        """
        active_budget = budget or self.budget
        max_context_tokens = active_budget.max_context_tokens

        seen_hashes: set[str] = set()
        unique_chunks: list[RerankResult | ScoredChunk] = []

        # 1. Deduplication: eliminate verbatim or near-verbatim duplicate chunks
        for c in chunks:
            text_content = c.text if isinstance(c, RerankResult) else (c.retrieval_text or c.content)
            h = self._content_hash(text_content)
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            unique_chunks.append(c)

        # 2. Sort by confidence / score descending (prioritize high-confidence evidence)
        sorted_chunks = sorted(unique_chunks, key=lambda x: x.score, reverse=True)

        # 3. Assemble chunks within token budget
        used_chunks: list[tuple[int, RerankResult | ScoredChunk, str, AssembledCitation]] = []
        current_tokens = 0
        dropped_count = 0

        element_counts = {"tables": 0, "equations": 0, "chemical_structures": 0}

        for idx, chunk in enumerate(sorted_chunks, start=1):
            if len(used_chunks) >= active_budget.max_chunks:
                dropped_count += 1
                continue

            # Extract fields
            if isinstance(chunk, RerankResult):
                cid = chunk.chunk_id
                did = chunk.document_id
                page = chunk.page_number
                section = chunk.section_title
                text_snippet = chunk.text
                bbox = chunk.metadata.get("bbox") if isinstance(chunk.metadata, dict) else None
                conf = chunk.score
            else:
                cid = chunk.chunk_id
                did = chunk.document_id
                page = chunk.page_number
                section = chunk.metadata.get("section_title") if isinstance(chunk.metadata, dict) else None
                text_snippet = chunk.display_text or chunk.retrieval_text or chunk.content
                bbox = chunk.bbox or (chunk.metadata.get("bbox") if isinstance(chunk.metadata, dict) else None)
                conf = chunk.score

            # Preserved element detection
            if TABLE_PATTERN.search(text_snippet) or getattr(chunk, "chunk_type", None) == ChunkType.TABLE:
                element_counts["tables"] += 1
            if EQUATION_PATTERN.search(text_snippet) or getattr(chunk, "chunk_type", None) == ChunkType.EQUATION:
                element_counts["equations"] += 1
            if SMILES_OR_INCHI_PATTERN.search(text_snippet) or getattr(chunk, "chunk_type", None) == ChunkType.CHEMICAL:
                element_counts["chemical_structures"] += 1

            citation_id = f"[{len(used_chunks) + 1}]"
            doc_title = (
                chunk.metadata.get("document_title") or "Document"
                if isinstance(chunk.metadata, dict)
                else "Document"
            )

            # Build formatted block with explicit provenance header
            header_parts = [f"Source {citation_id}: {doc_title}"]
            if section:
                header_parts.append(f"Section: {section}")
            if page is not None:
                header_parts.append(f"Page: {page}")

            formatted_snippet = f"### {' | '.join(header_parts)}\n{text_snippet.strip()}\n"
            snippet_tokens = estimate_tokens(formatted_snippet)

            if current_tokens + snippet_tokens > max_context_tokens:
                # Token budget reached
                dropped_count += 1
                continue

            citation = AssembledCitation(
                citation_id=citation_id,
                chunk_id=cid,
                document_id=did,
                title=doc_title,
                page_number=page,
                section_title=section,
                bbox=bbox,
                confidence=round(conf, 4),
            )

            used_chunks.append((len(used_chunks) + 1, chunk, formatted_snippet, citation))
            current_tokens += snippet_tokens

        # 4. Final context string construction
        context_blocks = [item[2] for item in used_chunks]
        final_context_text = "\n".join(context_blocks)
        total_tokens = estimate_tokens(final_context_text)

        citations_list = [item[3] for item in used_chunks]

        return AssembledContext(
            context_text=final_context_text,
            total_tokens=total_tokens,
            chunks_used_count=len(used_chunks),
            chunks_dropped_count=dropped_count + (len(unique_chunks) - len(sorted_chunks)),
            citations=citations_list,
            preserved_elements=element_counts,
        )
