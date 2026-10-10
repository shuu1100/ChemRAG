"""
ChemRAG — Experimental Parameter & Reaction Extractor Service
==============================================================
Extracts structured experimental procedures, chemical reactants, products,
solvents, catalysts, temperatures, pressures, and reported yields from text and tables.
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ExtractedExperiment(BaseModel):
    description: str
    temperature_celsius: Optional[float] = None
    pressure_bar: Optional[float] = None
    solvent: Optional[str] = None
    catalyst: Optional[str] = None
    reaction_time_hours: Optional[float] = None
    yield_percentage: Optional[float] = None
    reactants: List[str] = []
    products: List[str] = []
    confidence: float = 0.85


class ExperimentExtractor:
    """Extracts structured experimental data from scientific document text and tables."""

    def extract_from_text(self, text: str) -> List[ExtractedExperiment]:
        """Extract experimental records from raw text."""
        records: List[ExtractedExperiment] = []
        if not text or not text.strip():
            return records

        # Split text into paragraphs or procedural sentences
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]

        for p in paragraphs:
            # Check for experimental markers
            if not any(kw in p.lower() for kw in [
                "reaction", "yield", "stirred", "heated", "reflux", "synthesized",
                "added", "catalyst", "solvent", "temperature", "°c", "bar", "atm", "mmol"
            ]):
                continue

            # Extract Temperature
            temp = None
            temp_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:°C|deg\s*C|K)", p, re.IGNORECASE)
            if temp_match:
                val = float(temp_match.group(1))
                if "K" in temp_match.group(0):
                    val = val - 273.15
                temp = round(val, 1)

            # Extract Pressure
            pressure = None
            press_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:bar|atm|MPa|kPa)", p, re.IGNORECASE)
            if press_match:
                val = float(press_match.group(1))
                unit = press_match.group(0).lower()
                if "kpa" in unit:
                    val = val / 100.0
                elif "mpa" in unit:
                    val = val * 10.0
                pressure = round(val, 2)

            # Extract Yield
            yield_pct = None
            yield_match = re.search(r"(?:yield|obtained)[^\d]*(\d+(?:\.\d+)?)\s*%", p, re.IGNORECASE)
            if yield_match:
                yield_pct = float(yield_match.group(1))

            # Extract Reaction Time
            rtime = None
            time_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:h|hr|hours|min|minutes)", p, re.IGNORECASE)
            if time_match:
                val = float(time_match.group(1))
                if "min" in time_match.group(0).lower():
                    val = val / 60.0
                rtime = round(val, 2)

            # Extract Solvents
            solvent = None
            solvents = ["water", "ethanol", "methanol", "THF", "acetonitrile", "dcm", "ch2cl2", "toluene", "DMF", "DMSO", "ether", "acetone", "hexane"]
            for s in solvents:
                if re.search(r"\b" + s + r"\b", p, re.IGNORECASE):
                    solvent = s.upper() if s in ["thf", "dcm", "dmf", "dmso"] else s.capitalize()
                    break

            # Extract Catalysts
            catalyst = None
            catalysts = ["Pt/Al2O3", "Pd/C", "Ni", "H2SO4", "NaOH", "KOH", "CuI", "Rh", "Ru", "zeolite", "acid catalyst", "base"]
            for c in catalysts:
                if re.search(r"\b" + re.escape(c) + r"\b", p, re.IGNORECASE):
                    catalyst = c
                    break

            # Extract reactants / products heuristic mentions
            chemicals = re.findall(r"\b[A-Z][a-z0-9]*(?:-[A-Z][a-z0-9]*)*\b", p)
            chemicals = [c for c in chemicals if len(c) > 2 and c not in ["The", "And", "For", "With", "This", "After"]]

            rec = ExtractedExperiment(
                description=p[:300] + ("..." if len(p) > 300 else ""),
                temperature_celsius=temp,
                pressure_bar=pressure,
                solvent=solvent,
                catalyst=catalyst,
                reaction_time_hours=rtime,
                yield_percentage=yield_pct,
                reactants=chemicals[:3],
                products=chemicals[3:5],
                confidence=0.88 if (temp or yield_pct or solvent) else 0.70,
            )
            records.append(rec)

        return records
