# Phase 15 — API Design

## Goal
Expose a stable, typed backend API.

## Prompt 15.1 — REST API
Implement:
POST /documents/upload
GET /documents
GET /documents/{id}
DELETE /documents/{id}
POST /documents/{id}/process
GET /jobs/{id}
POST /search
POST /search/chemical
POST /chat
GET /citations/{id}
GET /documents/{id}/pages/{page}
POST /chemistry/validate
POST /chemistry/resolve
POST /evaluation/run
GET /health
GET /health/dependencies

Use Pydantic schemas, OpenAPI documentation, structured errors, authentication-ready dependency injection, and request IDs.

## Prompt 15.2 — Streaming API
Implement SSE for query progress and generation. Events should include query_received, planning, retrieval_started, retrieval_completed, reranking, chemical_validation, safety_check, generation, citation_validation, completed, and error. Never stream hidden reasoning.

## Exit Criteria
- OpenAPI is complete.
- API errors are consistent.
- Streaming is reconnect-safe where practical.
