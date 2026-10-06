# Phase 20 — Performance Optimization

## Goal
Benchmark before optimizing.

## Prompt 20.1 — Retrieval Benchmark
Benchmark corpora of approximately 10K, 100K, 500K, and 1M chunks where hardware permits. Measure semantic retrieval, lexical retrieval, RRF, reranking, filtered retrieval, and end-to-end query latency.

## Prompt 20.2 — HNSW Benchmark
Benchmark m, ef_construction, ef_search, iterative scan settings, scan limits, and vector/halfvec configurations. Measure recall, latency, RAM, index size, and build time. Choose settings empirically.

## Prompt 20.3 — Pipeline Optimization
Profile PDF parsing, OCSR, validation, embedding, database writes, retrieval, reranking, and LLM generation. Parallelize only independent work. Never sacrifice correctness for speed.

## Exit Criteria
- Performance bottlenecks are measured.
- HNSW settings have evidence behind them.
- Optimization decisions are documented.
