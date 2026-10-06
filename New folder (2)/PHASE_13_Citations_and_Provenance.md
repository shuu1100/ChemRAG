# Phase 13 — Citations and Provenance

## Goal
Make every generated scientific answer auditable against exact source locations.

## Prompt 13.1 — Citation Engine
Assign stable citation IDs to retrieved chunks such as `[CIT-001]`. Map each citation to chunk, page, bounding box, document, and source asset. The LLM receives valid citation IDs instead of inventing references.

## Prompt 13.2 — Citation Validator
After generation, extract claims, identify cited chunks, verify citation IDs, test whether citations support claims, detect uncited factual claims, and trigger regeneration or warning when evidence is insufficient. Never fabricate DOI/page/reference data.

## Prompt 13.3 — PDF.js Evidence Mapping
When a citation is clicked, open the source PDF, navigate to the page, convert stored coordinates to viewport coordinates, and render an overlay. Support zoom, rotation, scaling, and multi-page citations.

## Exit Criteria
- Every displayed citation resolves to a real source.
- Source highlights are visually aligned.
- Unsupported claims are detectable.
