# Phase 10 — Reranking

## Goal
Refine hybrid candidates with a cross-encoder.

## Prompt 10.1 — Reranker Interface
Create a `RerankerProvider` interface supporting local and hosted cross-encoders. Input: query + candidate chunks. Output: chunk ID, score, rank, model, latency.

## Prompt 10.2 — Cross-Encoder
Rerank the top 50–100 RRF candidates. Benchmark candidate pool sizes of 10, 20, 50, and 100. Measure MRR, nDCG, Recall@K, latency, and memory. Select a model based on results.

## Prompt 10.3 — Context Builder
Build the final LLM context. Remove duplicates, preserve hierarchy and provenance, preserve equations/chemical structures/table context, enforce token budgets, and prioritize high-confidence evidence. Never discard citation metadata.

## Exit Criteria
- Reranking demonstrably improves retrieval quality or its limitations are documented.
- Context construction is deterministic and provenance-preserving.
