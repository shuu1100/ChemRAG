# Phase 18 — Observability

## Goal
Make the complete system measurable and debuggable.

## Prompt 18.1 — Structured Logging
Implement JSON logs with request ID, user ID where available, tenant ID, document ID, query ID, agent run ID, latency, status, error, model, and provider.

## Prompt 18.2 — Tracing
Add OpenTelemetry-ready traces for API requests, retrieval, database queries, embeddings, reranking, agent execution, chemical validation, external APIs, LLM calls, and citation validation.

## Prompt 18.3 — Cost Tracking
Track LLM tokens, embedding usage, reranker calls, OCR/OCSR calls, external API calls, GPU inference time, and CPU processing time. Keep estimated cost separate from scientific outputs.

## Exit Criteria
- A complete user query can be traced end-to-end.
- Errors have enough context to debug.
- Provider usage is measurable.
