# Phase 07 — Chemical-Aware Chunking

## Goal
Create retrieval chunks without destroying chemical, mathematical, tabular, or procedural meaning.

## Prompt 7.1 — Semantic Chunker
Build document-aware chunking using sections, subsections, paragraphs, sentences, table rows, captions, equations, and SOP steps. Never split SMILES, InChI, chemical formulas, equations, reaction representations, table rows, safety warnings, or procedural steps.

## Prompt 7.2 — Chunk Metadata
Every chunk must contain chunk ID, document/version IDs, page, section, subsection, text, chunk type, bounding box, character offsets, chemical entity IDs, table/equation/image IDs, source hash, parser version, chunker version, and confidence. Keep frequently filtered fields relational and flexible metadata in JSONB.

## Prompt 7.3 — Contextual Enrichment
Generate retrieval-only contextual metadata such as title, section, subsection, table title, figure caption, chemical entities, experimental conditions, and document type. Preserve raw source text unchanged. Store raw_text, retrieval_text, and display_text separately.

## Exit Criteria
- Chemical strings are never arbitrarily split.
- Table rows retain headers.
- SOP steps preserve order.
- Every chunk can be traced to source geometry.
