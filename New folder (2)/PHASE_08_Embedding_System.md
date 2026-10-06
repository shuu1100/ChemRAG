# Phase 08 — Embedding System

## Goal
Implement provider-independent text and chemistry embeddings.

## Prompt 8.1 — Embedding Provider
Create an `EmbeddingProvider` interface supporting hosted and local models. The application must not know which provider generated a vector. Store model ID, version, dimension, normalization, timestamp, and provider.

## Prompt 8.2 — Text Embeddings
Generate embeddings for retrieval text in batches. Validate dimensions before database writes. Implement retry, timeout, batching, and failed-item handling.

## Prompt 8.3 — Chemical Embeddings
For chunks containing molecular structures, canonicalize structures and generate molecular embeddings using compatible chemistry models such as ChemBERTa or MoLFormer. Store chemical vectors separately from text vectors.

## Prompt 8.4 — Embedding Benchmark
Compare generic text embeddings, chemistry-aware embeddings, and combined retrieval. Measure Recall@K, MRR, nDCG, latency, memory, and storage. Choose defaults from measurements, not assumptions.

## Exit Criteria
- Embeddings are reproducible.
- Model metadata is stored.
- Local embedding mode works.
- Benchmark output is saved.
