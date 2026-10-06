# Phase 06 — Chemical Entity Normalization

## Goal
Extract, validate, normalize, and resolve chemical entities.

## Prompt 6.1 — Entity Extractor
Recognize chemical names, abbreviations, formulas, SMILES, InChI, InChIKey, CAS numbers, EC numbers, materials, solvents, catalysts, polymers, equipment, and process conditions. Store raw and normalized forms.

## Prompt 6.2 — RDKit Validation Service
Create an internal FastAPI chemical validation service using RDKit. For SMILES return valid/invalid, canonical SMILES, InChI, InChIKey, formula, molecular weight, atom count, bond count, formal charge, stereochemistry, and validation errors. Never expose arbitrary code execution.

## Prompt 6.3 — PubChem Resolver
Implement optional PubChem PUG REST integration for name, SMILES, InChI, InChIKey, and formula resolution. Retrieve CID, canonical/isomeric SMILES, InChI, InChIKey, formula, molecular weight, and synonyms. Add caching, rate limiting, retries, timeout, and negative caching. Keep PubChem optional so the core system works offline.

## Exit Criteria
- Chemical entities have stable identifiers.
- Invalid structures are detected.
- PubChem resolution is cached.
- Local RDKit functionality works without network access.
