# Phase 05 — Chemical Structure Recognition

## Goal
Detect chemical structure images and convert them into validated machine-readable representations.

## Prompt 5.1 — Chemical Image Detection
Detect candidate molecular structures, reaction schemes, plots, photographs, diagrams, and ordinary images. Store document assets and confidence scores. Do not run OCSR blindly over every image.

## Prompt 5.2 — DECIMER
Integrate DECIMER as the primary OCSR engine. Pipeline: image preprocessing → DECIMER → representation normalization → RDKit validation → confidence assessment. Store image ID, predicted representation, confidence, model version, processing time, and validation status. Do not assume every prediction is correct.

## Prompt 5.3 — MolScribe Fallback
Use MolScribe when DECIMER confidence is low, RDKit validation fails, image quality is poor, or structure complexity warrants verification. Compare outputs, normalize them, validate both, detect graph disagreement, and mark uncertain cases for review.

## Prompt 5.4 — Reaction Scheme Representation
Create a structured reaction representation containing reactants, products, reagents, catalysts, solvents, temperature, pressure, time, yield, conditions, and source citation. This phase is for document understanding and retrieval, not unrestricted synthesis planning.

## Exit Criteria
- Chemical images are detected.
- DECIMER and MolScribe are modular providers.
- RDKit validates outputs.
- Conflicting OCSR results are flagged.
