# Phase 04 — Scientific PDF Parsing

## Goal
Convert scientific PDFs into structured, spatially traceable intermediate representations.

## Prompt 4.1 — PyMuPDF Layout Extraction
Extract pages, text blocks, spans, coordinates, font metadata, images, page dimensions, and reading order where possible. Preserve spatial coordinates. Do not flatten the PDF immediately into plain text. Create a structured intermediate representation.

## Prompt 4.2 — GROBID Integration
Integrate GROBID for scholarly metadata and structure: title, authors, affiliations, abstract, sections, subsections, references, figures, captions, and equations where available. Map extracted content back to page provenance when possible.

## Prompt 4.3 — Marker/Math Extraction
Integrate Marker or an equivalent local parser for scientific formatting and difficult equations. Store raw equation, normalized representation, LaTeX, page, bounding box, and confidence. Never treat uncertain extraction as ground truth.

## Prompt 4.4 — Table Extraction
Create a dedicated table pipeline preserving title, caption, column headers, row headers, units, footnotes, rows, cells, coordinates, page, and bounding box. Produce both structured JSON and retrieval-friendly text where every row retains table context.

## Exit Criteria
- A scientific PDF becomes structured data.
- Page coordinates survive parsing.
- Tables preserve header context.
- Equations are represented separately.
- Parsing failures are explicit rather than silent.
