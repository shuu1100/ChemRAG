# Phase 03 — Document Ingestion

## Goal
Build reliable asynchronous document upload, classification, storage, and processing orchestration.

## Prompt 3.1 — Upload API
Implement `POST /documents/upload`. Validate PDF MIME type and extension, enforce file-size limits, calculate SHA-256, detect duplicates, persist metadata and the file, and create an asynchronous processing job. Return document ID, version ID, status, timestamp, and job ID. Do not parse synchronously.

## Prompt 3.2 — Document Classification
Classify documents as RESEARCH_PAPER, TEXTBOOK, EXPERIMENTAL_REPORT, SOP, SDS, TECHNICAL_REPORT, or UNKNOWN. Use structural/metadata heuristics first and allow an ML/VLM classifier later. Store confidence. Low-confidence documents should use the generic parser.

## Prompt 3.3 — Ingestion Worker
Implement an idempotent worker pipeline:
UPLOAD → VALIDATE → STORE → CLASSIFY → PARSE → EXTRACT → NORMALIZE → CHUNK → EMBED → INDEX → COMPLETE.
Every stage must be retryable, persisted, and resumable. Persist errors and processing timestamps.

## Exit Criteria
- Upload works.
- Duplicate files are detected.
- Background processing works.
- Failed jobs can resume.
- Job state survives backend restarts.
