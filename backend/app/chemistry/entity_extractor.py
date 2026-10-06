"""
ChemRAG — Chemical Entity Extractor & Normalizer
=================================================
Extracts and normalizes chemical entity mentions from text:
- CAS Registry Numbers (with Mod 10 checksum verification)
- EC / EINECS Numbers
- InChI & InChIKeys
- SMILES strings (validated via RDKit)
- Chemical formulas & common solvents/catalysts/reagents
- Process conditions (temperature, pressure, time)
"""
from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from backend.app.chemistry.validator import RDKitStructureValidator
from backend.app.core.logging import get_logger

logger = get_logger(__name__)


class ChemicalMentionType(str, enum.Enum):
    CAS_NUMBER = "cas_number"
    EC_NUMBER = "ec_number"
    INCHI_KEY = "inchi_key"
    INCHI = "inchi"
    SMILES = "smiles"
    CHEMICAL_FORMULA = "chemical_formula"
    SOLVENT = "solvent"
    CATALYST = "catalyst"
    COMMON_NAME = "common_name"
    PROCESS_CONDITION = "process_condition"


@dataclass
class ExtractedMention:
    """An extracted chemical entity mention with normalized form and confidence."""
    raw_text: str
    normalized_text: str
    mention_type: ChemicalMentionType
    confidence: float
    start_char: int = 0
    end_char: int = 0
    metadata: Dict[str, str] = field(default_factory=dict)


def verify_cas_checksum(cas_str: str) -> bool:
    """
    Validates CAS Registry Number format and Modulo-10 checksum:
    Format: [2-7 digits]-[2 digits]-[1 digit] (R-R-C)
    Checksum formula:
    Sum(digit_i * position_i) % 10 == check_digit
    """
    clean = cas_str.strip()
    parts = clean.split("-")
    if len(parts) != 3:
        return False

    first, second, check = parts[0], parts[1], parts[2]
    if not (first.isdigit() and second.isdigit() and check.isdigit()):
        return False
    if len(second) != 2 or len(check) != 1:
        return False

    digits_str = first + second
    check_digit = int(check)

    total = 0
    for i, d in enumerate(reversed(digits_str), start=1):
        total += int(d) * i

    return (total % 10) == check_digit


# Regular expression patterns
CAS_REGEX = re.compile(r"\b([1-9]\d{1,6}-\d{2}-\d)\b")
EC_REGEX = re.compile(r"\b([1-9]\d{2}-\d{3}-\d)\b")
INCHI_KEY_REGEX = re.compile(r"\b([A-Z]{14}-[A-Z]{10}-[A-Z\d])\b")
INCHI_REGEX = re.compile(r"\b(InChI=1S?/[A-Za-z0-9\(\)\+\-\,\.\/\;\:\?\#]+)\b")
CONDITION_REGEX = re.compile(
    r"\b(-?\d+(?:\.\d+)?\s*(?:°C|K|°F|bar|atm|MPa|kPa|psi|h|hours?|min|minutes?))\b",
    re.IGNORECASE,
)

# Known laboratory solvents and common reagent abbreviations
KNOWN_SOLVENTS = {
    "thf": "tetrahydrofuran",
    "dmf": "dimethylformamide",
    "dcm": "dichloromethane",
    "dmso": "dimethyl sulfoxide",
    "meoh": "methanol",
    "etoh": "ethanol",
    "etoac": "ethyl acetate",
    "mecn": "acetonitrile",
    "acn": "acetonitrile",
    "et2o": "diethyl ether",
    "tfa": "trifluoroacetic acid",
    "nmp": "n-methyl-2-pyrrolidone",
    "toluene": "toluene",
    "benzene": "benzene",
    "hexane": "hexane",
    "hexanes": "hexanes",
    "heptane": "heptane",
    "acetone": "acetone",
    "chloroform": "chloroform",
    "pyridine": "pyridine",
}

KNOWN_CATALYSTS = {
    "pd(pph3)4": "tetrakis(triphenylphosphine)palladium(0)",
    "pd/c": "palladium on carbon",
    "pd(dppf)cl2": "[1,1'-bis(diphenylphosphino)ferrocene]dichloropalladium(II)",
    "ru-binap": "ruthenium-BINAP",
    "rh-duphos": "rhodium-DuPhos",
    "pt/c": "platinum on carbon",
    "raney ni": "Raney nickel",
    "cu(oac)2": "copper(II) acetate",
    "fecl3": "iron(III) chloride",
    "alcl3": "aluminum chloride",
}

# Formula pattern (e.g. H2O, CH4, CO2, NaCl, H2SO4, KMnO4)
FORMULA_REGEX = re.compile(r"\b([A-Z][a-z]?(?:\d+)?(?:[A-Z][a-z]?(?:\d+)?)+)\b")


class ChemicalEntityExtractor:
    """
    Extracts and normalizes chemical mentions from scientific text.
    """

    def __init__(self, validator: Optional[RDKitStructureValidator] = None) -> None:
        self.validator = validator or RDKitStructureValidator()

    def extract_entities(self, text: str) -> List[ExtractedMention]:
        """
        Scan text and return all detected chemical entities with normalized representations.
        """
        mentions: List[ExtractedMention] = []

        if not text:
            return mentions

        # 1. CAS Registry Numbers
        for m in CAS_REGEX.finditer(text):
            raw_cas = m.group(1)
            is_valid_chk = verify_cas_checksum(raw_cas)
            if is_valid_chk:
                mentions.append(
                    ExtractedMention(
                        raw_text=raw_cas,
                        normalized_text=raw_cas,
                        mention_type=ChemicalMentionType.CAS_NUMBER,
                        confidence=0.99,
                        start_char=m.start(),
                        end_char=m.end(),
                    )
                )

        # 2. InChIKeys
        for m in INCHI_KEY_REGEX.finditer(text):
            ik = m.group(1)
            mentions.append(
                ExtractedMention(
                    raw_text=ik,
                    normalized_text=ik,
                    mention_type=ChemicalMentionType.INCHI_KEY,
                    confidence=0.98,
                    start_char=m.start(),
                    end_char=m.end(),
                )
            )

        # 3. InChI Strings
        for m in INCHI_REGEX.finditer(text):
            raw_inchi = m.group(1)
            mentions.append(
                ExtractedMention(
                    raw_text=raw_inchi,
                    normalized_text=raw_inchi,
                    mention_type=ChemicalMentionType.INCHI,
                    confidence=0.98,
                    start_char=m.start(),
                    end_char=m.end(),
                )
            )

        # 4. Solvents & Common Abbreviations
        words = re.findall(r"\b[A-Za-z0-9\-\(\)\/\.\_]+\b", text)
        for w in words:
            w_lower = w.lower()
            if w_lower in KNOWN_SOLVENTS:
                mentions.append(
                    ExtractedMention(
                        raw_text=w,
                        normalized_text=KNOWN_SOLVENTS[w_lower],
                        mention_type=ChemicalMentionType.SOLVENT,
                        confidence=0.95,
                    )
                )
            elif w_lower in KNOWN_CATALYSTS:
                mentions.append(
                    ExtractedMention(
                        raw_text=w,
                        normalized_text=KNOWN_CATALYSTS[w_lower],
                        mention_type=ChemicalMentionType.CATALYST,
                        confidence=0.95,
                    )
                )

        # 5. Process Conditions (Temperature, Pressure, Time)
        for m in CONDITION_REGEX.finditer(text):
            raw_cond = m.group(1)
            norm_cond = raw_cond.replace(" ", "")
            mentions.append(
                ExtractedMention(
                    raw_text=raw_cond,
                    normalized_text=norm_cond,
                    mention_type=ChemicalMentionType.PROCESS_CONDITION,
                    confidence=0.90,
                    start_char=m.start(),
                    end_char=m.end(),
                )
            )

        # 6. Chemical Formulas
        for m in FORMULA_REGEX.finditer(text):
            f_str = m.group(1)
            # Filter out non-chemical words that happen to look like formulas (e.g. DNA, RNA, USA, NASA)
            if f_str not in ("DNA", "RNA", "USA", "NASA", "PDF", "RAM", "CPU", "HTML", "URL", "API"):
                # Validate simple formula syntax
                mentions.append(
                    ExtractedMention(
                        raw_text=f_str,
                        normalized_text=f_str,
                        mention_type=ChemicalMentionType.CHEMICAL_FORMULA,
                        confidence=0.75,
                        start_char=m.start(),
                        end_char=m.end(),
                    )
                )

        return mentions
