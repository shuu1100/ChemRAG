"""
ChemRAG — Evaluation Dataset Schemas & Benchmark Loader
=========================================================
Covers benchmark item definitions across chemistry domains:
property lookup, reaction understanding, process engineering, materials,
SDS, experimental data, tables, equations, and chemical structure questions.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class BenchmarkCategory(str, Enum):
    PROPERTY_LOOKUP = "property_lookup"
    REACTION_UNDERSTANDING = "reaction_understanding"
    PROCESS_ENGINEERING = "process_engineering"
    MATERIALS_SCIENCE = "materials_science"
    SAFETY_SDS = "safety_sds"
    EXPERIMENTAL_DATA = "experimental_data"
    TABLES_AND_EQUATIONS = "tables_and_equations"
    STRUCTURE_QUESTIONS = "structure_questions"


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class BenchmarkItem:
    """Single benchmark evaluation test case."""
    id: str
    query: str
    category: BenchmarkCategory
    difficulty: DifficultyLevel
    expected_document_ids: List[str] = field(default_factory=list)
    expected_chunk_ids: List[str] = field(default_factory=list)
    expected_chemical_entities: List[str] = field(default_factory=list)
    expected_answer: Optional[str] = None
    query_smiles: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "category": self.category.value,
            "difficulty": self.difficulty.value,
            "expected_document_ids": self.expected_document_ids,
            "expected_chunk_ids": self.expected_chunk_ids,
            "expected_chemical_entities": self.expected_chemical_entities,
            "expected_answer": self.expected_answer,
            "query_smiles": self.query_smiles,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BenchmarkItem:
        return cls(
            id=data["id"],
            query=data["query"],
            category=BenchmarkCategory(data.get("category", "property_lookup")),
            difficulty=DifficultyLevel(data.get("difficulty", "medium")),
            expected_document_ids=data.get("expected_document_ids", []),
            expected_chunk_ids=data.get("expected_chunk_ids", []),
            expected_chemical_entities=data.get("expected_chemical_entities", []),
            expected_answer=data.get("expected_answer"),
            query_smiles=data.get("query_smiles"),
            tags=data.get("tags", []),
        )


def get_default_benchmark_dataset() -> List[BenchmarkItem]:
    """Returns curated default chemical research benchmark evaluation set."""
    return [
        BenchmarkItem(
            id="chem-eval-001",
            query="What is the boiling point and molar enthalpy of vaporization of ethanol at 1 atm?",
            category=BenchmarkCategory.PROPERTY_LOOKUP,
            difficulty=DifficultyLevel.EASY,
            expected_document_ids=["doc-101"],
            expected_chunk_ids=["c-001"],
            expected_chemical_entities=["Ethanol", "C2H6O"],
            expected_answer="Ethanol (C2H6O) has a boiling point of 78.37 °C at 1 atm and molar enthalpy of vaporization of 38.56 kJ/mol.",
            query_smiles="CCO",
            tags=["thermodynamics", "physical_properties"],
        ),
        BenchmarkItem(
            id="chem-eval-002",
            query="Explain the catalytic hydrogenation mechanism of bio-ethanol over Pt/Al2O3 catalysts.",
            category=BenchmarkCategory.REACTION_UNDERSTANDING,
            difficulty=DifficultyLevel.MEDIUM,
            expected_document_ids=["doc-102"],
            expected_chunk_ids=["c-002"],
            expected_chemical_entities=["Ethanol", "Platinum", "Alumina"],
            expected_answer="Pt/Al2O3 promotes ethanol dehydrogenation to acetaldehyde followed by high-selectivity gas-phase hydrogenation.",
            query_smiles="CCO",
            tags=["catalysis", "reactions"],
        ),
        BenchmarkItem(
            id="chem-eval-003",
            query="Describe the binary vapor-liquid phase equilibrium positive deviation from Raoult's law for ethanol-water.",
            category=BenchmarkCategory.PROCESS_ENGINEERING,
            difficulty=DifficultyLevel.HARD,
            expected_document_ids=["doc-103"],
            expected_chunk_ids=["c-003"],
            expected_chemical_entities=["Ethanol", "Water"],
            expected_answer="Ethanol-water forms an azeotrope at 89.5 mole% ethanol due to strong hydrogen bonding non-ideality.",
            tags=["phase_equilibria", "azeotrope"],
        ),
        BenchmarkItem(
            id="chem-eval-004",
            query="What are the GHS hazard statements and recommended PPE for handling concentrated Ethanol (CAS 64-17-5)?",
            category=BenchmarkCategory.SAFETY_SDS,
            difficulty=DifficultyLevel.EASY,
            expected_document_ids=["doc-104"],
            expected_chemical_entities=["Ethanol", "CAS 64-17-5"],
            expected_answer="H225: Highly flammable liquid and vapor. H319: Causes serious eye irritation. Use chemical splash goggles and flame-resistant lab coats.",
            tags=["sds", "safety", "ghs"],
        ),
        BenchmarkItem(
            id="chem-eval-005",
            query="Validate SMILES valency and formula for structure C1=CC=CC=C1 and calculate heavy atom count.",
            category=BenchmarkCategory.STRUCTURE_QUESTIONS,
            difficulty=DifficultyLevel.EASY,
            expected_chemical_entities=["Benzene", "C6H6"],
            expected_answer="Benzene (C6H6) is valid with 6 heavy carbon atoms and 0 formal charge.",
            query_smiles="c1ccccc1",
            tags=["rdkit", "valency", "structure"],
        ),
    ]
