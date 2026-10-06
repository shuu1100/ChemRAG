# Phase 23 — Final Integration

## Goal
Integrate every completed subsystem into a coherent end-to-end ChemRAG.

## Prompt 23.1 — End-to-End Pipeline
Integrate document upload → classification → parsing → tables/equations/images → OCSR → chemical normalization → chunking → embeddings → PostgreSQL → hybrid retrieval → RRF → reranking → LangGraph → safety → answer → citation validation → PDF evidence viewer. Create an end-to-end test.

## Prompt 23.2 — Golden Demo
Create a deterministic demo corpus containing a research paper, experimental report, SDS, SOP, and textbook chapter with structures, tables, equations, experimental conditions, and safety information. Create representative queries across every modality.

## Prompt 23.3 — Failure Testing
Test corrupted/empty/huge/scanned PDFs, bad OCR, invalid SMILES, ambiguous chemical names, missing headers, incorrect reading order, duplicates, conflicting sources, missing embeddings, database/Redis/LLM/OCSR failures, API timeouts, prompt injection, and unsafe requests. Ensure graceful failure.

## Exit Criteria
- Golden demo passes.
- Failure modes are observable.
- End-to-end citations work.
