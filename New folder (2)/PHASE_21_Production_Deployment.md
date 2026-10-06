# Phase 21 — Production Deployment

## Goal
Prepare ChemRAG for reliable deployment.

## Prompt 21.1 — Production Docker
Create multi-stage production images, minimal dependencies, non-root users, health checks, resource limits, and correct signal handling.

## Prompt 21.2 — Production Database
Configure connection pooling, migrations, backups, indexes, vacuum strategy, monitoring, query logging, and vector index maintenance. Do not blindly copy development settings.

## Prompt 21.3 — Deployment Architecture
Document single-server, cloud VM, managed PostgreSQL, GPU worker, frontend hosting, object storage, Redis, reverse proxy, TLS, and secret-management options. Keep the design vendor-neutral.

## Exit Criteria
- Production containers build.
- Deployment documentation is reproducible.
- Secrets are externalized.
