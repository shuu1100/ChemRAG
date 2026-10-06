# Phase 09 — Hybrid Retrieval

## Goal
Implement semantic, lexical, chemical, filtered, and fused retrieval.

## Prompt 9.1 — Semantic Retriever
Implement pgvector cosine retrieval with configurable top-K, metadata filters, document/section/date/tenant filters, and chemical filters. Use HNSW and configurable query-time search parameters.

## Prompt 9.2 — Lexical Retriever
Implement PostgreSQL full-text search using `tsvector`, GIN, query parsing, ranking, and highlighting. Add trigram search for exact technical identifiers such as CAS numbers and equipment IDs. Keep the interface replaceable so BM25/OpenSearch can be introduced later. Do not label `ts_rank_cd` as BM25.

## Prompt 9.3 — Chemical Retriever
Implement exact identity, formula, InChIKey, name, similarity, and substructure retrieval where supported. Clearly distinguish identity matching, molecular similarity, and text similarity.

## Prompt 9.4 — RRF
Fuse semantic, lexical, and optional chemical results using `RRF_score = Σ 1/(k + rank_i)`, default k=60 and configurable. Store component ranks and scores.

## Prompt 9.5 — Filtered ANN
Use pgvector iterative scans where appropriate. Support strict/relaxed order and configurable scan limits. Benchmark recall under highly selective metadata filters rather than claiming perfect recall.

## Exit Criteria
- Hybrid search returns deterministic ranked results.
- Exact chemical identifiers are retrievable.
- RRF improves benchmark results where expected.
- Filtered ANN behavior is measured.
