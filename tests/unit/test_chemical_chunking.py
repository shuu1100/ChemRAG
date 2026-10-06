"""
ChemRAG — Chemical-Aware Chunking Tests
=======================================
Tests:
- Chemical strings (SMILES, InChI) are NEVER split arbitrarily across chunks
- Table rows retain column headers and context
- Procedural SOP steps preserve sequence order
- Every chunk is traceable to source geometry (BoundingBox)
- Contextual enrichment preserves raw source text unchanged
"""
from __future__ import annotations

import uuid
import pytest

from backend.app.chunking.atomic_units import AtomicUnitGuard
from backend.app.chunking.chemical_chunker import ChemicalAwareChunker
from backend.app.chunking.models import ChunkPayload
from backend.app.models.chunk import ChunkType
from backend.app.parsing.models import (
    BoundingBox,
    ParsedBlock,
    ParsedDocument,
    ParsedEquation,
    ParsedLine,
    ParsedPage,
    ParsedSpan,
    ParsedTable,
)


class TestAtomicUnitGuard:
    def test_identifies_smiles_and_inchi_atomic_spans(self) -> None:
        text = (
            "We synthesized aspirin (SMILES: CC(=O)Oc1ccccc1C(=O)O) and caffeine "
            "(InChI=1S/C8H10N4O2/c1-10-4-9-6-5(10)7(13)12(3)8(14)11(6)2/h4H,1-3H3) yesterday."
        )
        guard = AtomicUnitGuard()
        spans = guard.find_atomic_spans(text)

        assert len(spans) >= 2
        # Verify that splitting inside the SMILES or InChI is disallowed
        smiles_idx = text.index("CC(=O)Oc1ccccc1C(=O)O") + 5
        assert guard.is_safe_split_point(text, smiles_idx, spans) is False

        # Verify that splitting outside in whitespace is allowed
        outside_idx = text.index(" yesterday.")
        assert guard.is_safe_split_point(text, outside_idx, spans) is True

    def test_adjust_split_boundary_avoids_splitting_chemical_string(self) -> None:
        text = "Catalyst used was c1cc(ccc1C)Br in high yield."
        guard = AtomicUnitGuard()
        spans = guard.find_atomic_spans(text)

        inside_smiles = text.index("c1cc(ccc1C)Br") + 4
        safe_idx = guard.adjust_split_to_safe_boundary(text, inside_smiles, spans)
        assert guard.is_safe_split_point(text, safe_idx, spans) is True


class TestChemicalAwareChunker:
    def test_table_rows_retain_headers_in_chunks(self) -> None:
        table = ParsedTable(
            table_index=1,
            caption="Table 1: Hydrogenation Optimization",
            bbox=BoundingBox(50, 100, 500, 200),
            page_number=1,
            headers=["Catalyst", "Solvent", "Temp (°C)", "Yield (%)"],
            rows=[
                ["Ru-BINAP", "MeOH", "60", "94"],
                ["Rh-DuPhos", "THF", "25", "88"],
            ],
            units={"Temp (°C)": "°C", "Yield (%)": "%"},
        )
        table.generate_retrieval_text()

        doc = ParsedDocument(
            doc_id="doc-123",
            filename="reaction.pdf",
            page_count=1,
            title="Asymmetric Synthesis Study",
            tables=[table],
            pages=[ParsedPage(page_number=1, width=595, height=842, raw_text="Sample text")],
        )

        chunker = ChemicalAwareChunker()
        chunks = chunker.chunk_document(doc)

        table_chunks = [c for c in chunks if c.chunk_type == ChunkType.TABLE]
        assert len(table_chunks) >= 1

        t_chunk = table_chunks[0]
        # Bounding box survives
        assert t_chunk.bbox is not None
        assert t_chunk.bbox.width > 0
        # Headers retained in contextual retrieval text
        assert "Catalyst: Ru-BINAP" in t_chunk.retrieval_text
        assert "Yield (%): 94" in t_chunk.retrieval_text
        assert "Catalyst: Rh-DuPhos" in t_chunk.retrieval_text
        assert "[Document: Asymmetric Synthesis Study]" in t_chunk.retrieval_text

    def test_sop_steps_preserve_order_and_grouping(self) -> None:
        sop_text = (
            "Standard Operating Procedure: Balance Calibration\n"
            "Step 1.1: Verify balance pan is free from debris.\n"
            "Step 1.2: Place 10.000 g calibration mass on the center of the pan.\n"
            "Step 1.3: Record the displayed reading in the calibration logbook.\n"
            "Step 1.4: Repeat measurement three times and calculate standard deviation."
        )

        block = ParsedBlock(
            block_id=1,
            text=sop_text,
            bbox=BoundingBox(50, 100, 500, 300),
            lines=[ParsedLine(text=sop_text, bbox=BoundingBox(50, 100, 500, 300))],
        )
        page = ParsedPage(page_number=1, width=595, height=842, blocks=[block], raw_text=sop_text)
        doc = ParsedDocument(doc_id="sop-1", filename="sop.pdf", page_count=1, pages=[page])

        chunker = ChemicalAwareChunker()
        chunks = chunker.chunk_document(doc)

        assert len(chunks) >= 1
        c = chunks[0]
        assert c.metadata.get("has_sop_steps") is True
        # Steps are in exact sequential order
        idx_1 = c.raw_text.index("Step 1.1")
        idx_2 = c.raw_text.index("Step 1.2")
        idx_3 = c.raw_text.index("Step 1.3")
        idx_4 = c.raw_text.index("Step 1.4")
        assert idx_1 < idx_2 < idx_3 < idx_4

    def test_every_chunk_traceable_to_source_geometry(self) -> None:
        block = ParsedBlock(
            block_id=1,
            text="General reaction conditions were applied under nitrogen atmosphere.",
            bbox=BoundingBox(72.0, 150.0, 480.0, 200.0),
        )
        page = ParsedPage(page_number=3, width=595, height=842, blocks=[block], raw_text="text")
        doc = ParsedDocument(doc_id="test", filename="test.pdf", page_count=3, pages=[page])

        chunker = ChemicalAwareChunker()
        chunks = chunker.chunk_document(doc)

        assert len(chunks) == 1
        c = chunks[0]
        assert c.page_number == 3
        assert c.bbox is not None
        assert c.bbox.x0 == 72.0
        assert c.bbox.y0 == 150.0
        assert c.bbox.x1 == 480.0
        assert c.bbox.y1 == 200.0

    def test_contextual_enrichment_preserves_raw_source_text(self) -> None:
        source_paragraph = "4-bromotoluene was coupled with phenylboronic acid using Pd(PPh3)4 in THF."
        block = ParsedBlock(
            block_id=1,
            text=source_paragraph,
            bbox=BoundingBox(50, 100, 450, 150),
        )
        page = ParsedPage(page_number=1, width=595, height=842, blocks=[block], raw_text=source_paragraph)
        doc = ParsedDocument(
            doc_id="cross-coupling",
            filename="suzuki.pdf",
            page_count=1,
            title="Palladium Catalysis",
            pages=[page],
        )

        chunker = ChemicalAwareChunker()
        chunks = chunker.chunk_document(doc)

        assert len(chunks) == 1
        c = chunks[0]

        # Raw source text is 100% UNTOUCHED
        assert c.raw_text == source_paragraph

        # Retrieval text is enriched with document metadata & chemical entities
        assert "[Document: Palladium Catalysis]" in c.retrieval_text
        assert "[Chemicals:" in c.retrieval_text
        assert source_paragraph in c.retrieval_text

        # Display text is clean
        assert c.display_text == source_paragraph
