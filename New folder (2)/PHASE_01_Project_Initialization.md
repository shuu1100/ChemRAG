# Phase 01 — Project Initialization

## Goal
Establish the ChemRAG repository, development conventions, local infrastructure, configuration, and engineering rules.

## Prompt 1.1 — Repository Architecture
You are the lead software architect for ChemRAG. Inspect the existing repository before changing anything. Create a modular monorepo with `backend/`, `frontend/`, `infra/`, `scripts/`, `docs/`, and `tests/`. The backend should contain modules for API, core configuration, database, models, schemas, repositories, services, ingestion, parsing, chemistry, embeddings, retrieval, reranking, agents, safety, evaluation, and observability. The frontend should use React + TypeScript + Vite with components, pages, features, hooks, services, stores, types, and utilities. Create `.env.example`, Docker configuration, `README.md`, `pyproject.toml`, and package configuration. Do not implement business logic yet. Explain why each major directory exists.

## Prompt 1.2 — Docker Infrastructure
Create a local development environment containing PostgreSQL 16+ with pgvector, Redis, GROBID, backend, and frontend. Add persistent PostgreSQL volumes, health checks, startup dependencies, environment configuration, and clear start/stop commands. Verify connectivity to every service.

## Prompt 1.3 — Configuration System
Implement typed configuration using Pydantic Settings. Create configuration groups for database, Redis, storage, LLM, embeddings, reranker, GROBID, DECIMER, MolScribe, PubChem, security, safety, observability, and evaluation. Every external provider must support enabled/disabled state, base URL, API key when applicable, timeout, retries, and rate limits. Provide development/test/production configuration modes and tests.

## Exit Criteria
- Repository builds.
- Docker services start.
- Backend health endpoint works.
- PostgreSQL and Redis connectivity tests pass.
- No secrets are committed.
- Documentation explains setup.
