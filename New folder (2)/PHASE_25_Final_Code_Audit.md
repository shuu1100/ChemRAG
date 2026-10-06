# Phase 25 — Final Code Audit

## Goal
Perform a production-readiness audit before declaring ChemRAG complete.

## Prompt
Do not immediately modify code. Inspect the entire repository first.

Audit:
architecture, security, database, migrations, API, frontend, PDF parsing, OCSR, chemistry validation, chunking, embeddings, retrieval, RRF, reranking, LangGraph, safety, citations, evaluation, logging, performance, Docker, deployment, tests, and documentation.

Look for:
dead code, duplication, missing error handling, hard-coded secrets, hard-coded providers, incorrect chemical assumptions, vector-dimension mistakes, database indexing problems, N+1 queries, unbounded queues, memory leaks, blocking async code, missing timeouts, citation hallucinations, prompt-injection vulnerabilities, tool bypasses, tenant-isolation problems, provenance errors, weak tests, and missing documentation.

Produce:
1. Critical issues
2. High-priority issues
3. Medium-priority issues
4. Low-priority issues
5. Architecture recommendations
6. Performance bottlenecks
7. Security vulnerabilities
8. Scientific correctness issues
9. Missing tests
10. Production readiness score

Only implement changes after presenting the audit.
