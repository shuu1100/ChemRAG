# Phase 26 — Final Acceptance Test

## Goal
Evaluate ChemRAG as an external engineering team would.

## Prompt
Run the complete acceptance suite.

### Document ingestion
Verify research papers, textbooks, experimental reports, SDS, SOP, and technical reports.

### Parsing
Verify reading order, tables, equations, chemical images, page coordinates, and sections.

### Chemistry
Verify chemical structure recognition, SMILES validation, normalization, name resolution, and molecular identifiers.

### Retrieval
Verify semantic search, lexical search, chemical search, RRF, metadata filtering, and reranking.

### Generation
Verify evidence-grounded answers, citations, uncertainty, and refusal to invent sources.

### Provenance
Verify citation click → original page → exact highlighted region.

### Safety
Verify malicious document instructions cannot control the agent, and unsafe tool calls cannot bypass the safety guard.

### Reliability
Simulate database, Redis, LLM, OCSR, external API, and PDF parser failures.

### Evaluation
Verify retrieval, RAG, chemistry, citation, and safety metrics are automated and stored.

Do not claim production readiness unless the acceptance tests actually pass.

Produce a final report containing:
- passed tests
- failed tests
- known limitations
- performance results
- security status
- scientific limitations
- deployment status
- recommended next steps
