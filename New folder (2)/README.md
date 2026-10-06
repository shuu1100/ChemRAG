# ChemRAG Phase Prompt Pack

This folder contains the ChemRAG implementation prompts split into independent Markdown files.

## Recommended workflow

1. Give your coding agent the project master specification from your original research document.
2. Start with Phase 01.
3. Let the agent implement only that phase.
4. Run the tests and inspect the result.
5. Proceed to the next phase.
6. Do not implement the LangGraph agent layer before the core RAG pipeline is working.

## Build priority

The most important MVP path is:

PDF → structured parsing → provenance → chemical-aware chunks → embeddings → PostgreSQL/pgvector → hybrid retrieval → RRF → reranking → grounded answer → citation → PDF highlight.

After that, add OCSR, chemical retrieval, LangGraph, safety, and advanced evaluation.

## Files

There is one Markdown file for every implementation phase plus a master index.
