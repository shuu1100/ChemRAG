# Phase 16 — External Data Sources

## Goal
Integrate optional public scientific metadata and chemical information sources without making the core system network-dependent.

## Prompt 16.1 — PubChem
Integrate PubChem PUG REST with caching, rate limits, retries, timeouts, and timestamped storage. Support compound lookup by name, SMILES, InChI, InChIKey, and formula.

## Prompt 16.2 — Scientific Metadata
Create a provider abstraction supporting optional Crossref, OpenAlex, Semantic Scholar, PubMed/NCBI, and arXiv metadata providers. Use them for publication metadata, authors, DOI, dates, abstracts, and citation metadata. Do not automatically download copyrighted full text.

## Exit Criteria
- External providers can be disabled.
- Offline core functionality remains usable.
- Cached results prevent unnecessary API calls.
