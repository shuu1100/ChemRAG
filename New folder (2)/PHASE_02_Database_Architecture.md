# Phase 02 — Database Architecture

## Goal
Build the PostgreSQL/pgvector data model with provenance, multi-document support, chemical entities, retrieval metadata, jobs, agent state, safety, and evaluation.

## Prompt 2.1 — Database Schema
Design and implement PostgreSQL tables for users, organizations, documents, document_versions, document_pages, document_assets, document_sections, chunks, chunk_embeddings, chemical_entities, chemical_structures, chunk_chemical_entities, tables, table_rows, experiments, citations, ingestion_jobs, retrieval_queries, retrieval_results, agent_runs, tool_calls, safety_events, evaluation_runs, evaluation_cases, and audit_logs. Support document lineage, page provenance, bounding boxes, chunk versioning, multiple embedding types, chemical structures, tenant isolation, soft deletion, timestamps, hashes, processing states, and errors.

## Prompt 2.2 — Provenance Schema
Create a reusable provenance model linking every extracted object to document ID, document version, page, source asset, bounding box, character offsets when available, parser name/version, extraction timestamp, and confidence. It must support text, tables, equations, chemical structures, images, chunks, and citations.

## Prompt 2.3 — pgvector
Install pgvector and create model-independent vector storage. Support text, chemical, and optional image embeddings. Use HNSW where appropriate. Support configurable vector dimensions and half precision where compatible. Do not hard-code performance claims. Add migrations and benchmark scripts.

## Exit Criteria
- Alembic migrations work from an empty database.
- Foreign keys and indexes are validated.
- Provenance can map a chunk back to a page and bounding box.
- Vector columns and indexes are created successfully.
