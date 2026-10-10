"""
ChemRAG — Chemical-Aware Semantic Document Chunker
===================================================
Produces retrieval chunks preserving chemical strings, equations,
table rows with header context, and procedural SOP steps.
Generates distinct raw_text, retrieval_text, and display_text.
Ensures every chunk is traceable to source page geometry.
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from backend.app.chemistry.entity_extractor import ChemicalEntityExtractor
from backend.app.chunking.atomic_units import AtomicUnitGuard
from backend.app.chunking.models import ChunkPayload
from backend.app.core.logging import get_logger
from backend.app.models.chunk import ChunkType
from backend.app.parsing.models import BoundingBox, ParsedDocument, ParsedPage

logger = get_logger(__name__)


def estimate_token_count(text: str) -> int:
    """Fast robust token count approximation (~4 chars/token or word-based)."""
    if not text:
        return 0
    words = len(text.split())
    chars = len(text)
    return max(words, int(chars / 4.0))


class ChemicalAwareChunker:
    """
    Document-aware, chemistry-safe semantic chunking engine.
    """

    def __init__(
        self,
        target_tokens: int = 350,
        max_tokens: int = 550,
        overlap_tokens: int = 40,
        entity_extractor: Optional[ChemicalEntityExtractor] = None,
    ) -> None:
        self.target_tokens = target_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.guard = AtomicUnitGuard()
        self.entity_extractor = entity_extractor or ChemicalEntityExtractor()

    def chunk_document(
        self,
        doc: ParsedDocument,
        document_id: Optional[uuid.UUID] = None,
        version_id: Optional[uuid.UUID] = None,
    ) -> List[ChunkPayload]:
        """
        Processes a parsed document into structured, contextually enriched chunks.
        """
        chunks: List[ChunkPayload] = []
        chunk_idx = 0
        doc_title = doc.title or doc.filename

        # 1. Process Extracted Tables as Dedicated Table Chunks
        for table in doc.tables:
            table_raw = table.retrieval_text or table.raw_html or table.caption
            retrieval_text = (
                f"[Document: {doc_title}] [Page {table.page_number}] {table.caption}\n\n"
                f"{table.retrieval_text}"
            )

            # Detect chemical mentions in table
            mentions = self.entity_extractor.extract_entities(table_raw)
            chem_entities = list(dict.fromkeys(m.normalized_text for m in mentions))

            chunk = ChunkPayload(
                document_id=document_id,
                version_id=version_id,
                page_number=table.page_number,
                chunk_index=chunk_idx,
                chunk_type=ChunkType.TABLE,
                raw_text=table_raw,
                retrieval_text=retrieval_text,
                display_text=table.retrieval_text,
                bbox=table.bbox,
                chemical_entities=chem_entities,
                asset_ids=[f"table_{table.table_index}"],
                token_count=estimate_token_count(retrieval_text),
                metadata={"table_index": table.table_index, "caption": table.caption},
            )
            chunks.append(chunk)
            chunk_idx += 1

        # 2. Process Extracted Display Equations as Dedicated Equation Chunks
        for eq in doc.equations:
            eq_raw = f"{eq.raw_text}\nLaTeX: {eq.latex}"
            retrieval_text = (
                f"[Document: {doc_title}] [Page {eq.page_number}] [Equation {eq.equation_index}]\n\n"
                f"{eq_raw}"
            )

            chunk = ChunkPayload(
                document_id=document_id,
                version_id=version_id,
                page_number=eq.page_number,
                chunk_index=chunk_idx,
                chunk_type=ChunkType.EQUATION,
                raw_text=eq.raw_text,
                retrieval_text=retrieval_text,
                display_text=f"$${eq.latex}$$",
                bbox=eq.bbox,
                confidence=eq.confidence,
                token_count=estimate_token_count(retrieval_text),
                metadata={"equation_index": eq.equation_index, "latex": eq.latex},
            )
            chunks.append(chunk)
            chunk_idx += 1

        # 3. Process Pages & Section Text
        for page in doc.pages:
            page_chunks = self._chunk_page_text(
                page=page,
                doc_title=doc_title,
                document_id=document_id,
                version_id=version_id,
                start_index=chunk_idx,
            )
            chunks.extend(page_chunks)
            chunk_idx += len(page_chunks)

        logger.info(
            "Chemical-aware chunking completed",
            doc_title=doc_title,
            total_chunks=len(chunks),
        )
        return chunks

    def _chunk_page_text(
        self,
        page: ParsedPage,
        doc_title: str,
        document_id: Optional[uuid.UUID],
        version_id: Optional[uuid.UUID],
        start_index: int,
    ) -> List[ChunkPayload]:
        """Chunks narrative page blocks respecting atomic spans and procedural order."""
        chunks: List[ChunkPayload] = []
        if not page.blocks:
            if page.raw_text and page.raw_text.strip():
                from backend.app.parsing.models import ParsedBlock
                page_blocks = [
                    ParsedBlock(
                        block_id=0,
                        block_type="text",
                        text=page.raw_text.strip(),
                        bbox=BoundingBox(x0=0.0, y0=0.0, x1=getattr(page, "width", 612.0) or 612.0, y1=getattr(page, "height", 792.0) or 792.0),
                    )
                ]
            else:
                return chunks
        else:
            page_blocks = page.blocks

        # Group page blocks into coherent sections or paragraphs
        current_text_parts: List[str] = []
        current_tokens = 0
        current_bbox: Optional[BoundingBox] = None
        current_idx = start_index

        for block in page_blocks:
            block_text = block.text.strip()
            if not block_text:
                continue

            block_tokens = estimate_token_count(block_text)

            # Update accumulated bounding box
            if current_bbox is None:
                current_bbox = block.bbox
            elif block.bbox:
                current_bbox = BoundingBox(
                    x0=min(current_bbox.x0, block.bbox.x0),
                    y0=min(current_bbox.y0, block.bbox.y0),
                    x1=max(current_bbox.x1, block.bbox.x1),
                    y1=max(current_bbox.y1, block.bbox.y1),
                )

            # If adding this block exceeds target tokens, finalize chunk
            if current_tokens + block_tokens > self.max_tokens and current_text_parts:
                combined_raw = "\n\n".join(current_text_parts)
                chunk = self._build_text_chunk(
                    raw_text=combined_raw,
                    doc_title=doc_title,
                    page_number=page.page_number,
                    chunk_index=current_idx,
                    bbox=current_bbox,
                    document_id=document_id,
                    version_id=version_id,
                )
                chunks.append(chunk)
                current_idx += 1

                # Reset accumulator
                current_text_parts = [block_text]
                current_tokens = block_tokens
                current_bbox = block.bbox
            else:
                current_text_parts.append(block_text)
                current_tokens += block_tokens

        # Flush remaining text
        if current_text_parts:
            combined_raw = "\n\n".join(current_text_parts)
            chunk = self._build_text_chunk(
                raw_text=combined_raw,
                doc_title=doc_title,
                page_number=page.page_number,
                chunk_index=current_idx,
                bbox=current_bbox,
                document_id=document_id,
                version_id=version_id,
            )
            chunks.append(chunk)

        return chunks

    def _build_text_chunk(
        self,
        raw_text: str,
        doc_title: str,
        page_number: int,
        chunk_index: int,
        bbox: Optional[BoundingBox],
        document_id: Optional[uuid.UUID],
        version_id: Optional[uuid.UUID],
    ) -> ChunkPayload:
        """Enriches raw text with retrieval context without mutating raw source text."""
        # Detect chemical entities in text
        mentions = self.entity_extractor.extract_entities(raw_text)
        chem_entities = list(dict.fromkeys(m.normalized_text for m in mentions))

        # Check for procedural SOP steps to maintain order flag
        has_sop_steps = bool(re.search(r"^(?:Step\s+)?\d+(?:\.\d+)*[:\.]", raw_text, re.MULTILINE))

        # Contextual prefix (Prompt 7.3)
        context_parts = [f"[Document: {doc_title}]", f"[Page: {page_number}]"]
        if chem_entities:
            context_parts.append(f"[Chemicals: {', '.join(chem_entities[:5])}]")

        retrieval_text = " ".join(context_parts) + "\n\n" + raw_text

        return ChunkPayload(
            document_id=document_id,
            version_id=version_id,
            page_number=page_number,
            chunk_index=chunk_index,
            chunk_type=ChunkType.TEXT,
            raw_text=raw_text,
            retrieval_text=retrieval_text,
            display_text=raw_text,
            bbox=bbox,
            chemical_entities=chem_entities,
            token_count=estimate_token_count(retrieval_text),
            metadata={"has_sop_steps": has_sop_steps},
        )
