# Phase 17 — Evaluation

## Goal
Build a rigorous evaluation system for retrieval, generation, chemistry understanding, citations, and safety.

## Prompt 17.1 — Retrieval Dataset
Create a benchmark format containing query, expected documents/chunks, expected chemical entities, optional expected answer, difficulty, and category. Include property lookup, reaction understanding, process engineering, materials, SDS, experimental data, tables, equations, and structure questions.

## Prompt 17.2 — Retrieval Metrics
Implement Recall@1/5/10/20, MRR, nDCG, Precision@K, latency, and storage/compute metrics for semantic, lexical, chemical, RRF, and reranked retrieval.

## Prompt 17.3 — RAG Evaluation
Integrate RAGAS-style evaluation for Context Precision, Context Recall, Faithfulness, and Answer Relevance. Store model versions and evaluation runs. Treat LLM-as-judge metrics as measurements, not absolute truth.

## Prompt 17.4 — Chemistry Evaluation
Create safe domain tests covering stoichiometry, chemical identity, formulas, structure validation, units, thermodynamic reasoning, mass balance, reaction interpretation, experimental tables, and SDS retrieval.

## Prompt 17.5 — Regression Suite
Run retrieval, chemistry, citation, safety, API, and frontend smoke tests on every relevant code/model/index change. Detect regressions automatically.

## Exit Criteria
- Evaluation is reproducible.
- Results are persisted.
- Regression tests can be run from CI.
