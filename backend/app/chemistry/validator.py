"""
ChemRAG — RDKit Structure Validator & Normalizer
=================================================
Validates predicted SMILES from OCSR models (DECIMER, MolScribe).
Enforces chemical valency, generates canonical SMILES and InChIKey,
calculates molecular formula and weight, and compares molecular graph equivalence.
Never assumes model predictions are correct without RDKit verification.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from rdkit import Chem
from rdkit.Chem import rdMolDescriptors


from backend.app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class StructureValidationResult:
    """Outcome of RDKit chemical structure validation."""
    is_valid: bool
    raw_smiles: str
    canonical_smiles: Optional[str] = None
    inchi: Optional[str] = None
    inchi_key: Optional[str] = None
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    heavy_atom_count: int = 0
    ring_count: int = 0
    error: Optional[str] = None

    @property
    def has_error(self) -> bool:
        return not self.is_valid or self.error is not None


class RDKitStructureValidator:
    """
    Validates and standardizes chemical structures.
    """

    def validate_smiles(self, raw_smiles: str) -> StructureValidationResult:
        """
        Validates raw SMILES string with RDKit and normalizes to canonical representation.
        """
        if not raw_smiles or not raw_smiles.strip():
            return StructureValidationResult(
                is_valid=False,
                raw_smiles=raw_smiles,
                error="Empty or whitespace SMILES input",
            )

        clean_smiles = raw_smiles.strip()

        try:
            # Parse and sanitize molecular structure
            mol = Chem.MolFromSmiles(clean_smiles, sanitize=True)
            if mol is None:
                return StructureValidationResult(
                    is_valid=False,
                    raw_smiles=clean_smiles,
                    error="RDKit failed to parse structure (valence error, invalid aromaticity, or syntax error)",
                )

            # Generate Canonical SMILES (preserving stereochemistry)
            canonical_smiles = Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)

            # Generate InChI & InChIKey
            inchi = Chem.MolToInchi(mol)
            inchi_key = Chem.InchiToInchiKey(inchi) if inchi else None

            formula = rdMolDescriptors.CalcMolFormula(mol)
            mw = round(float(rdMolDescriptors.CalcExactMolWt(mol)), 3)


            heavy_atoms = mol.GetNumHeavyAtoms()
            rings = rdMolDescriptors.CalcNumRings(mol)

            return StructureValidationResult(
                is_valid=True,
                raw_smiles=clean_smiles,
                canonical_smiles=canonical_smiles,
                inchi=inchi,
                inchi_key=inchi_key,
                molecular_formula=formula,
                molecular_weight=mw,
                heavy_atom_count=heavy_atoms,
                ring_count=rings,
            )

        except Exception as exc:
            err = f"RDKit validation exception: {exc}"
            logger.debug("SMILES validation failed with exception", smiles=clean_smiles, error=err)
            return StructureValidationResult(
                is_valid=False,
                raw_smiles=clean_smiles,
                error=err,
            )

    def compare_structures(self, smiles_a: str, smiles_b: str) -> Tuple[bool, str]:
        """
        Compares two SMILES strings for graph equivalence.
        Returns (is_equivalent, detail_message).
        """
        res_a = self.validate_smiles(smiles_a)
        res_b = self.validate_smiles(smiles_b)

        if not res_a.is_valid and not res_b.is_valid:
            return False, "Both structures are invalid"
        if not res_a.is_valid:
            return False, f"First structure is invalid: {res_a.error}"
        if not res_b.is_valid:
            return False, f"Second structure is invalid: {res_b.error}"

        # InChIKey is the gold standard for canonical identity
        if res_a.inchi_key and res_b.inchi_key:
            if res_a.inchi_key == res_b.inchi_key:
                return True, "Identical InChIKey"
            # Check constitutional match (first 14 chars of InChIKey ignore stereochemistry)
            if res_a.inchi_key[:14] == res_b.inchi_key[:14]:
                return False, "Stereoisomeric disagreement (same constitution, different stereochemistry)"

        if res_a.canonical_smiles == res_b.canonical_smiles:
            return True, "Identical canonical SMILES"

        return False, f"Graph disagreement: '{res_a.canonical_smiles}' != '{res_b.canonical_smiles}'"
