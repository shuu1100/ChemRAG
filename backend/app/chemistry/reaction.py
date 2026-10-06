"""
ChemRAG — Structured Reaction Scheme Representation
====================================================
Structured chemical reaction representation containing reactants, products,
reagents, catalysts, solvents, conditions (temp, pressure, time), yield,
and source citation.
Designed for document understanding and retrieval (not unrestricted synthesis planning).
"""
from __future__ import annotations

import enum
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


class ParticipantRole(str, enum.Enum):
    REACTANT = "reactant"
    PRODUCT = "product"
    REAGENT = "reagent"
    CATALYST = "catalyst"
    SOLVENT = "solvent"


@dataclass
class ReactionParticipant:
    """A chemical species participating in a reaction."""
    name: str
    role: ParticipantRole
    smiles: Optional[str] = None
    inchi_key: Optional[str] = None
    amount: Optional[str] = None
    stoichiometry: Optional[float] = None  # molar equivalents


@dataclass
class ReactionConditions:
    """Operational parameters for a chemical reaction."""
    temperature_celsius: Optional[float] = None
    pressure_bar: Optional[float] = None
    time_hours: Optional[float] = None
    atmosphere: Optional[str] = None  # e.g., "N2", "Ar", "H2 (10 bar)", "air"
    ph: Optional[float] = None
    raw_conditions_text: Optional[str] = None


@dataclass
class ReactionScheme:
    """
    Complete structured representation of a chemical reaction scheme.
    """
    scheme_id: str
    title: str
    reactants: List[ReactionParticipant] = field(default_factory=list)
    products: List[ReactionParticipant] = field(default_factory=list)
    catalysts: List[ReactionParticipant] = field(default_factory=list)
    solvents: List[ReactionParticipant] = field(default_factory=list)
    reagents: List[ReactionParticipant] = field(default_factory=list)
    conditions: Optional[ReactionConditions] = None
    yield_pct: Optional[float] = None
    source_citation: Optional[str] = None
    page_number: int = 1
    confidence: float = 1.0

    def to_retrieval_summary(self) -> str:
        """
        Produces context-rich textual summary optimized for dense/sparse embedding retrieval.
        """
        lines = [f"[Reaction Scheme: {self.title or self.scheme_id}]"]

        if self.reactants:
            r_str = " + ".join(f"{r.name}" + (f" ({r.smiles})" if r.smiles else "") for r in self.reactants)
            lines.append(f"Reactants: {r_str}")

        if self.products:
            p_str = " + ".join(f"{p.name}" + (f" ({p.smiles})" if p.smiles else "") for p in self.products)
            lines.append(f"Products: {p_str}")

        if self.catalysts:
            c_str = ", ".join(c.name for c in self.catalysts)
            lines.append(f"Catalysts: {c_str}")

        if self.reagents:
            reg_str = ", ".join(f"{r.name}" + (f" ({r.amount})" if r.amount else "") for r in self.reagents)
            lines.append(f"Reagents: {reg_str}")

        if self.solvents:
            s_str = ", ".join(s.name for s in self.solvents)
            lines.append(f"Solvents: {s_str}")

        if self.conditions:
            cond_parts = []
            if self.conditions.temperature_celsius is not None:
                cond_parts.append(f"{self.conditions.temperature_celsius} °C")
            if self.conditions.pressure_bar is not None:
                cond_parts.append(f"{self.conditions.pressure_bar} bar")
            if self.conditions.time_hours is not None:
                cond_parts.append(f"{self.conditions.time_hours} h")
            if self.conditions.atmosphere:
                cond_parts.append(f"{self.conditions.atmosphere} atmosphere")
            if self.conditions.raw_conditions_text:
                cond_parts.append(self.conditions.raw_conditions_text)
            if cond_parts:
                lines.append(f"Conditions: {', '.join(cond_parts)}")

        if self.yield_pct is not None:
            lines.append(f"Yield: {self.yield_pct}%")

        if self.source_citation:
            lines.append(f"Citation: {self.source_citation}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert reaction scheme to dictionary/JSON."""
        return {
            "scheme_id": self.scheme_id,
            "title": self.title,
            "reactants": [asdict(r) for r in self.reactants],
            "products": [asdict(p) for p in self.products],
            "catalysts": [asdict(c) for c in self.catalysts],
            "solvents": [asdict(s) for s in self.solvents],
            "reagents": [asdict(reg) for reg in self.reagents],
            "conditions": asdict(self.conditions) if self.conditions else None,
            "yield_pct": self.yield_pct,
            "source_citation": self.source_citation,
            "page_number": self.page_number,
            "confidence": self.confidence,
        }
