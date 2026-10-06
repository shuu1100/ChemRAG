# Phase 11 — LangGraph Agent System

## Goal
Add stateful, constrained agent orchestration only after retrieval is reliable.

## Prompt 11.1 — Graph State
Create strongly typed LangGraph state containing query, conversation ID, tenant ID, intent, subtasks, retrieval queries, retrieved/reranked chunks, chemical entities, tool calls, safety decision, answer, citations, confidence, and errors.

## Prompt 11.2 — Planner
Implement a Planner Agent that classifies questions, identifies evidence needs, decides whether retrieval/chemical validation/calculation is needed, decomposes complex questions, and routes tasks. It must not execute arbitrary code.

## Prompt 11.3 — Retrieval Agent
Generate search variants, execute semantic/lexical/chemical retrieval, perform RRF and reranking, and return evidence. Never fabricate evidence.

## Prompt 11.4 — Chemistry Agent
Support safe operations such as SMILES validation, normalization, molecular properties, identity lookup, and document-based chemical reasoning. Do not provide unrestricted autonomous laboratory execution.

## Prompt 11.5 — Analytics Agent
Support unit conversion, mass balance, molar calculations, concentration, stoichiometric calculations, statistics, and experimental data analysis. Return inputs, units, formula, result, and assumptions.

## Prompt 11.6 — Aggregator
Synthesize evidence, distinguish evidence from inference, attach citations, identify contradictions, and state uncertainty. Never silently resolve conflicting sources.

## Exit Criteria
- Agent graph has explicit nodes and transitions.
- Tools are invoked through controlled interfaces.
- No hidden chain-of-thought is exposed in the UI.
