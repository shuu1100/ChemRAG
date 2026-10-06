# Phase 12 — Safety and Compliance

## Goal
Create a dedicated, non-bypassable safety layer for chemistry-related tool execution.

## Prompt 12.1 — Policy Engine
Build a policy engine that takes chemical entities, requested action, document context, user role, and query intent. Return ALLOW, ALLOW_WITH_WARNING, REQUIRE_REVIEW, or REFUSE. Store policy rules externally in configuration/database.

## Prompt 12.2 — Restricted Chemical Screening
Normalize chemical entities using CAS, InChIKey, canonical SMILES, and synonyms before screening against authoritative restricted-chemical datasets where legally appropriate. Store matched rule, chemical ID, decision, timestamp, and policy version.

## Prompt 12.3 — Tool Guard
Enforce Agent → Safety Guard → Policy Decision → Tool. No agent prompt may bypass this layer. Test prompt injection, malicious documents, tool injection, obfuscated names, and attempts to manipulate policy decisions.

## Exit Criteria
- Every chemistry tool call passes through the guard.
- Safety decisions are logged.
- Safety policy is independently testable.
