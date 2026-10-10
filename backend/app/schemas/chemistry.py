"""
ChemRAG — Chemistry Validation & Normalization API Schemas
==========================================================
Pydantic schemas for RDKit structure validation, PubChem resolution,
and chemical entity extraction.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ValidateSmilesRequest(BaseModel):
    """Request payload to validate a SMILES string."""
    smiles: str = Field(..., description="Chemical SMILES representation to validate")


class ValidateSmilesResponse(BaseModel):
    """RDKit validation outcome for a chemical structure."""
    valid: bool
    raw_smiles: str
    canonical_smiles: Optional[str] = None
    inchi: Optional[str] = None
    inchi_key: Optional[str] = None
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    heavy_atom_count: int = 0
    bond_count: int = 0
    formal_charge: int = 0
    num_chiral_centers: int = 0
    structure_svg: Optional[str] = None
    validation_error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ResolveCompoundRequest(BaseModel):
    """Request to resolve a compound using PubChem."""
    query: str = Field(..., description="Chemical name, SMILES, or InChIKey")
    query_type: str = Field(default="name", description="Query type: 'name', 'smiles', or 'inchikey'")


class ResolveCompoundResponse(BaseModel):
    """PubChem resolution output."""
    found: bool
    cid: Optional[int] = None
    canonical_smiles: Optional[str] = None
    inchi: Optional[str] = None
    inchi_key: Optional[str] = None
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    iupac_name: Optional[str] = None
    structure_svg: Optional[str] = None
    structure_url: Optional[str] = None
    data_source: Optional[str] = None
    message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ExtractEntitiesRequest(BaseModel):
    """Request to extract chemical entities from text."""
    text: str = Field(..., description="Scientific text to scan for chemical mentions")


class ExtractedMentionItem(BaseModel):
    """Single extracted mention."""
    raw_text: str
    normalized_text: str
    mention_type: str
    confidence: float
    start_char: int
    end_char: int


class ExtractEntitiesResponse(BaseModel):
    """Extracted chemical entities response."""
    mentions: List[ExtractedMentionItem]
    count: int

    model_config = ConfigDict(from_attributes=True)
