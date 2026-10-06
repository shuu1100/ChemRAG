# Phase 22 — Free-First Deployment

## Goal
Make a usable version of ChemRAG possible without mandatory paid APIs.

## Prompt 22.1 — Local Free Stack
Create a fully local mode using PostgreSQL, pgvector, Redis, GROBID, RDKit, DECIMER/MolScribe where hardware allows, local Hugging Face embeddings, local reranker, and local LLM where hardware permits. Clearly report unavailable capabilities rather than failing silently.

## Prompt 22.2 — Low-Cost Cloud Mode
Design a low-cost configuration using static frontend hosting, small backend VM, PostgreSQL, optional Redis, optional GPU worker, configurable LLM provider, asynchronous OCSR worker, and object storage. No component should be permanently vendor-locked.

## Exit Criteria
- Core RAG can run without paid APIs.
- External providers are optional.
- Hardware-dependent features degrade gracefully.
