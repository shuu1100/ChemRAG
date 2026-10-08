"""
ChemRAG — Chemistry Agent
==========================
Fulfills Phase 11 / Prompt 11.4:
- Safe chemistry operations: SMILES validation, sanitization, canonicalization.
- Molecular properties extraction (MW, formula, InChIKey, TPSA, LogP, donors/acceptors).
- Identity lookup (PubChem resolver integration).
- Document-based chemical reasoning.
- Safety: Strictly prevents autonomous laboratory execution or dangerous synthesis.
"""
from __future__ import annotations

import re
import time
from typing import Any, Optional

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Lipinski, rdMolDescriptors
    RDKIT_AVAILABLE = True
except (ImportError, Exception):
    Chem = None
    Descriptors = None
    Lipinski = None
    rdMolDescriptors = None
    RDKIT_AVAILABLE = False

from backend.app.agents.state import (
    AgentState,
    ChemicalEntityData,
    ToolCallRecord,
)
from backend.app.chemistry.pubchem_resolver import PubChemResolver
from backend.app.chemistry.validator import RDKitStructureValidator
from backend.app.core.logging import get_logger

logger = get_logger(__name__)


class ChemistryAgent:
    """
    Constrained Chemistry Reasoning and Validation Agent.
    Interacts with RDKit and PubChem to validate and characterize molecules safely.
    """

    def __init__(self, pubchem_resolver: Optional[PubChemResolver] = None) -> None:
        self.pubchem = pubchem_resolver or PubChemResolver()
        self.validator = RDKitStructureValidator()
        self.logger = logger

    def validate_and_characterize_smiles(self, smiles: str) -> Optional[ChemicalEntityData]:
        """
        Safely validate and compute properties for a SMILES string using RDKit.
        Returns None if SMILES is syntactically invalid or fails valence checks.
        """
        clean_smiles = smiles.strip()
        val_result = self.validator.validate_smiles(clean_smiles)
        if not val_result.is_valid:
            return None

        if Chem is None:
            return ChemicalEntityData(
                smiles=clean_smiles,
                canonical_smiles=val_result.canonical_smiles or clean_smiles,
                inchi=val_result.inchi,
                inchi_key=val_result.inchi_key,
                molecular_formula=val_result.molecular_formula,
                molecular_weight=val_result.molecular_weight,
                properties={
                    "heavy_atom_count": val_result.heavy_atom_count,
                    "ring_count": val_result.ring_count,
                },
                source="validator_characterization",
            )

        mol = Chem.MolFromSmiles(clean_smiles)
        if mol is None:
            return None

        canon_smiles = Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)
        inchi = Chem.MolToInchi(mol)
        inchi_key = Chem.MolToInchiKey(mol)
        formula = rdMolDescriptors.CalcMolFormula(mol) if rdMolDescriptors else "CxHyOz"
        mw = round(float(Descriptors.ExactMolWt(mol)), 4) if Descriptors else 100.0
        tpsa = round(float(Descriptors.TPSA(mol)), 2) if Descriptors else 0.0
        logp = round(float(Descriptors.MolLogP(mol)), 2) if Descriptors else 0.0
        hbd = int(Lipinski.NumHDonors(mol)) if Lipinski else 0
        hba = int(Lipinski.NumHAcceptors(mol)) if Lipinski else 0
        rot_bonds = int(Lipinski.NumRotatableBonds(mol)) if Lipinski else 0

        return ChemicalEntityData(
            smiles=clean_smiles,
            canonical_smiles=canon_smiles,
            inchi=inchi,
            inchi_key=inchi_key,
            molecular_formula=formula,
            molecular_weight=mw,
            properties={
                "tpsa": tpsa,
                "logp": logp,
                "h_bond_donors": hbd,
                "h_bond_acceptors": hba,
                "rotatable_bonds": rot_bonds,
                "heavy_atom_count": mol.GetNumHeavyAtoms(),
            },
            source="rdkit_characterization",
        )

    async def lookup_by_name_or_cas(self, identifier: str) -> Optional[ChemicalEntityData]:
        """Look up chemical properties via PubChem resolver."""
        record = await self.pubchem.resolve(identifier)
        if not record:
            return None

        return ChemicalEntityData(
            name=record.iupac_name or identifier,
            smiles=record.smiles,
            canonical_smiles=record.canonical_smiles or record.smiles,
            inchi=record.inchi,
            inchi_key=record.inchi_key,
            molecular_formula=record.molecular_formula,
            molecular_weight=record.molecular_weight,
            cas_number=identifier if re.match(r"^\d{2,7}-\d{2}-\d$", identifier) else None,
            properties={
                "cid": record.cid,
                "synonyms": record.synonyms[:5] if record.synonyms else [],
            },
            source="pubchem_lookup",
        )

    def extract_chemical_mentions(self, text: str) -> list[str]:
        """Extract candidate chemical identifiers (SMILES, CAS, common chemicals) from text."""
        candidates: list[str] = []

        # 1. CAS registry numbers: \d{2,7}-\d{2}-\d
        cas_matches = re.findall(r"\b\d{2,7}-\d{2}-\d\b", text)
        candidates.extend(cas_matches)

        # 2. Known common chemicals in text
        known_names = [
            "aspirin", "acetylsalicylic acid", "benzene", "paracetamol", "acetaminophen",
            "caffeine", "ibuprofen", "ethanol", "acetone", "toluene", "glucose",
            "phenol", "aniline", "benzoic acid", "methanol", "acetic acid",
        ]
        text_lower = text.lower()
        for name in known_names:
            if re.search(rf"\b{name}\b", text_lower):
                candidates.append(name)

        # 3. Explicit SMILES tokens
        words = text.split()
        for w in words:
            w_clean = w.strip(",;.:()")
            if len(w_clean) >= 3 and any(c in w_clean for c in ["=", "#", "@", "[", "]", "/", "\\"]):
                if Chem is not None:
                    if Chem.MolFromSmiles(w_clean) is not None:
                        candidates.append(w_clean)
                else:
                    if self.validator.validate_smiles(w_clean).is_valid:
                        candidates.append(w_clean)

        return list(dict.fromkeys(candidates))

    async def run(self, state: AgentState) -> AgentState:
        """Run chemistry agent node in the LangGraph graph."""
        query = state.get("query", "")
        scratchpad = list(state.get("internal_scratchpad", []))
        tool_calls = list(state.get("tool_calls", []))
        known_entities = list(state.get("chemical_entities", []))

        t0 = time.perf_counter()
        scratchpad.append(f"[ChemistryAgent] Analyzing chemical entities for query: '{query}'")

        # 1. Extract candidates from query
        candidates = self.extract_chemical_mentions(query)

        # Also extract from retrieved chunks if available
        for chunk in state.get("retrieved_chunks", [])[:3]:
            candidates.extend(self.extract_chemical_mentions(chunk.content))

        candidates = list(dict.fromkeys(candidates))
        scratchpad.append(f"[ChemistryAgent] Found candidate chemical entities: {candidates}")

        new_entities: list[ChemicalEntityData] = []
        for cand in candidates:
            # Check if it is a valid SMILES
            entity_data = self.validate_and_characterize_smiles(cand)
            if entity_data:
                new_entities.append(entity_data)
                continue

            # Otherwise attempt PubChem lookup by name or CAS
            pub_data = await self.lookup_by_name_or_cas(cand)
            if pub_data:
                # If PubChem returned a SMILES, compute full RDKit properties
                if pub_data.smiles:
                    rdkit_data = self.validate_and_characterize_smiles(pub_data.smiles)
                    if rdkit_data:
                        rdkit_data.name = pub_data.name or cand
                        rdkit_data.cas_number = pub_data.cas_number
                        new_entities.append(rdkit_data)
                        continue
                new_entities.append(pub_data)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # Record tool invocation
        tool_calls.append(
            ToolCallRecord(
                tool_name="chemical_validation_and_characterization",
                input_args={"query": query, "candidates": candidates},
                output_result=f"Validated {len(new_entities)} chemical entities",
                execution_time_ms=round(elapsed_ms, 2),
                status="success",
            )
        )

        all_entities = known_entities + new_entities
        scratchpad.append(f"[ChemistryAgent] Successfully characterized {len(new_entities)} entities ({elapsed_ms:.1f}ms)")

        # Mark subtask completed
        subtasks = list(state.get("subtasks", []))
        for st in subtasks:
            if st.target_agent == "chemistry":
                st.status = "completed"
                st.output_data = {"entities_characterized": len(new_entities)}

        return {
            **state,
            "chemical_entities": all_entities,
            "tool_calls": tool_calls,
            "subtasks": subtasks,
            "internal_scratchpad": scratchpad,
        }
