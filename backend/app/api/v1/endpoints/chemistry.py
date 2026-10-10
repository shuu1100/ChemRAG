"""
ChemRAG — Chemistry Validation & Normalization API Endpoints
============================================================
Endpoints:
- POST /chemistry/validate          (RDKit structure validation and descriptor extraction)
- POST /chemistry/resolve           (PubChem PUG REST resolution with caching)
- POST /chemistry/extract-entities  (Regex and rule-based chemical entity extraction)
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors

from backend.app.chemistry.entity_extractor import ChemicalEntityExtractor
from backend.app.chemistry.pubchem_resolver import PubChemResolver
from backend.app.chemistry.validator import RDKitStructureValidator
from backend.app.core.logging import get_logger
from backend.app.schemas.chemistry import (
    ExtractEntitiesRequest,
    ExtractEntitiesResponse,
    ExtractedMentionItem,
    ResolveCompoundRequest,
    ResolveCompoundResponse,
    ValidateSmilesRequest,
    ValidateSmilesResponse,
)

logger = get_logger(__name__)
router = APIRouter()

validator = RDKitStructureValidator()
entity_extractor = ChemicalEntityExtractor(validator=validator)
pubchem_resolver = PubChemResolver()


@router.post(
    "/validate",
    response_model=ValidateSmilesResponse,
    summary="Validate chemical structure using RDKit",
)
async def validate_chemical_smiles(
    payload: ValidateSmilesRequest,
) -> ValidateSmilesResponse:
    """
    Validates chemical valency, returns canonical SMILES, InChI, InChIKey,
    molecular formula, molecular weight, heavy atom count, bond count,
    formal charge, stereochemical centers, and 2D SVG structure depiction.
    """
    raw_smiles = payload.smiles.strip()
    res = validator.validate_smiles(raw_smiles)

    if not res.is_valid:
        return ValidateSmilesResponse(
            valid=False,
            raw_smiles=raw_smiles,
            validation_error=res.error,
        )

    # Calculate additional structural features using RDKit
    mol = Chem.MolFromSmiles(res.canonical_smiles or raw_smiles)
    bond_count = mol.GetNumBonds() if mol else 0
    formal_charge = Chem.GetFormalCharge(mol) if mol else 0
    chiral_centers = len(Chem.FindMolChiralCenters(mol, includeUnassigned=True)) if mol else 0
    svg = validator.generate_structure_svg(res.canonical_smiles or raw_smiles)

    return ValidateSmilesResponse(
        valid=True,
        raw_smiles=raw_smiles,
        canonical_smiles=res.canonical_smiles,
        inchi=res.inchi,
        inchi_key=res.inchi_key,
        molecular_formula=res.molecular_formula,
        molecular_weight=res.molecular_weight,
        heavy_atom_count=res.heavy_atom_count,
        bond_count=bond_count,
        formal_charge=formal_charge,
        num_chiral_centers=chiral_centers,
        structure_svg=svg,
        validation_error=None,
    )


@router.post(
    "/resolve",
    response_model=ResolveCompoundResponse,
    summary="Resolve compound via PubChem and RDKit with 2D structure generation",
)
async def resolve_compound(
    payload: ResolveCompoundRequest,
) -> ResolveCompoundResponse:
    """
    Resolves a chemical name, SMILES, or InChIKey against PubChem PUG REST or local RDKit.
    Generates 2D SVG structure depictions and provides structure image URLs.
    """
    q = payload.query.strip()
    q_type = payload.query_type.lower().strip()

    record = None
    if q_type == "name":
        record = await pubchem_resolver.resolve_by_name(q)
    elif q_type == "smiles":
        record = await pubchem_resolver.resolve_by_smiles(q)
    elif q_type == "inchikey":
        record = await pubchem_resolver.resolve_by_inchikey(q)
    
    if not record:
        record = await pubchem_resolver.resolve(q)

    if record:
        smiles = record.canonical_smiles or ""
        svg = validator.generate_structure_svg(smiles) if smiles else None
        struct_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{record.cid}/PNG" if record.cid else None

        # Enrich missing property fields (formula, MW, inchi_key) via RDKit
        formula = record.molecular_formula
        mw = record.molecular_weight
        inchi = record.inchi
        inchi_key = record.inchi_key

        if smiles and (not formula or not mw or not inchi_key):
            val = validator.validate_smiles(smiles)
            if val.is_valid:
                formula = formula or val.molecular_formula
                mw = mw or val.molecular_weight
                inchi = inchi or val.inchi
                inchi_key = inchi_key or val.inchi_key

        return ResolveCompoundResponse(
            found=True,
            cid=record.cid,
            canonical_smiles=record.canonical_smiles,
            inchi=inchi,
            inchi_key=inchi_key,
            molecular_formula=formula,
            molecular_weight=mw,
            iupac_name=record.iupac_name or q,
            structure_svg=svg,
            structure_url=struct_url,
            data_source="PubChem + RDKit",
            message="Successfully resolved compound from PubChem.",
        )

    # Local RDKit fallback if PubChem did not return a record
    res = validator.validate_smiles(q)
    if res.is_valid and res.canonical_smiles:
        svg = validator.generate_structure_svg(res.canonical_smiles)
        return ResolveCompoundResponse(
            found=True,
            canonical_smiles=res.canonical_smiles,
            inchi=res.inchi,
            inchi_key=res.inchi_key,
            molecular_formula=res.molecular_formula,
            molecular_weight=res.molecular_weight,
            iupac_name=q,
            structure_svg=svg,
            data_source="RDKit Local Validator",
            message="Resolved structure locally via RDKit.",
        )

    return ResolveCompoundResponse(
        found=False,
        message=f"Compound not found for query '{q}' in PubChem or RDKit.",
    )


@router.get(
    "/resolve",
    response_model=ResolveCompoundResponse,
    summary="Resolve compound via PubChem and RDKit (GET)",
)
async def resolve_compound_get(
    query: str,
    query_type: str = "name",
) -> ResolveCompoundResponse:
    """
    GET query parameter endpoint for compound structure resolution.
    """
    return await resolve_compound(ResolveCompoundRequest(query=query, query_type=query_type))


@router.post(
    "/extract-entities",
    response_model=ExtractEntitiesResponse,
    summary="Extract chemical entity mentions from text",
)
async def extract_chemical_entities(
    payload: ExtractEntitiesRequest,
) -> ExtractEntitiesResponse:
    """
    Extracts CAS numbers (with checksum verification), InChIKeys, formulas,
    solvents, catalysts, and reaction conditions from scientific text.
    """
    mentions = entity_extractor.extract_entities(payload.text)
    items = [
        ExtractedMentionItem(
            raw_text=m.raw_text,
            normalized_text=m.normalized_text,
            mention_type=m.mention_type.value,
            confidence=m.confidence,
            start_char=m.start_char,
            end_char=m.end_char,
        )
        for m in mentions
    ]
    return ExtractEntitiesResponse(mentions=items, count=len(items))
