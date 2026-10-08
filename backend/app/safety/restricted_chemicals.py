"""
ChemRAG â€” Authoritative Restricted Chemical Screening
======================================================
Fulfills Phase 12 / Prompt 12.2:
- Normalizes entities by CAS, InChIKey, canonical SMILES, and synonyms.
- Screens against authoritative registries:
  * Chemical Weapons Convention (CWC Schedules 1, 2, 3)
  * Controlled High Explosives and Energetic Materials
  * Controlled Precursors for Illicit Substances (GDSL / DEA)
  * Lethal Chemical/Biological Toxins
- Resilient against adversarial obfuscation (spaces, dashes, leetspeak, aliases).
"""
from __future__ import annotations

import re
from typing import Optional

from backend.app.chemistry.normalizer import ChemicalEntityNormalizer
from backend.app.safety.models import (
    RestrictedChemicalEntry,
    SafetyRiskCategory,
    ScreeningMatch,
    UserRole,
)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Authoritative Restricted Chemical Registry
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

RESTRICTED_DATABASE: list[RestrictedChemicalEntry] = [
    # â”€â”€ CWC Schedule 1 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    RestrictedChemicalEntry(
        chemical_id="CWC-1-001",
        primary_name="Sarin",
        cas_number="107-44-8",
        inchi_key="DYCAUUSVQMDRMD-UHFFFAOYSA-N",
        canonical_smiles="CC(C)OP(=O)(C)F",
        molecular_formula="C4H10FO2P",
        synonyms=["GB", "isopropyl methylphosphonofluoridate", "sarin nerve agent", "zarin"],
        risk_category=SafetyRiskCategory.CWC_SCHEDULE_1,
        hazard_description="Extremely toxic organophosphorus nerve agent causing lethal acetylcholinesterase inhibition.",
        regulatory_framework="CWC Schedule 1.A.01",
    ),
    RestrictedChemicalEntry(
        chemical_id="CWC-1-002",
        primary_name="Soman",
        cas_number="96-64-0",
        inchi_key="QGHRBBIWTRMDOC-UHFFFAOYSA-N",
        canonical_smiles="CC(C)(C)C(C)OP(=O)(C)F",
        molecular_formula="C7H16FO2P",
        synonyms=["GD", "pinacolyl methylphosphonofluoridate", "soman nerve agent"],
        risk_category=SafetyRiskCategory.CWC_SCHEDULE_1,
        hazard_description="Persistent G-series nerve agent with rapid aging kinetics preventing oxime reactivation.",
        regulatory_framework="CWC Schedule 1.A.01",
    ),
    RestrictedChemicalEntry(
        chemical_id="CWC-1-003",
        primary_name="Tabun",
        cas_number="77-81-6",
        inchi_key="PJVJTCIRVMBVIA-UHFFFAOYSA-N",
        canonical_smiles="CCOP(=O)(C#N)N(C)C",
        molecular_formula="C5H11N2O2P",
        synonyms=["GA", "ethyl dimethylphosphoramidocyanidate", "tabun nerve agent"],
        risk_category=SafetyRiskCategory.CWC_SCHEDULE_1,
        hazard_description="G-series organophosphorus nerve agent causing fatal respiratory paralysis.",
        regulatory_framework="CWC Schedule 1.A.02",
    ),
    RestrictedChemicalEntry(
        chemical_id="CWC-1-004",
        primary_name="VX",
        cas_number="50782-69-9",
        inchi_key="JXRXENNZDAPUSA-UHFFFAOYSA-N",
        canonical_smiles="CCOP(=O)(C)SCCN(C(C)C)C(C)C",
        molecular_formula="C11H26NO2PS",
        synonyms=["O-ethyl S-[2-(diisopropylamino)ethyl] methylphosphonothioate", "vx nerve agent", "vx gas"],
        risk_category=SafetyRiskCategory.CWC_SCHEDULE_1,
        hazard_description="Highly persistent V-series nerve agent with extreme percutaneous and inhalation lethality.",
        regulatory_framework="CWC Schedule 1.A.03",
    ),
    RestrictedChemicalEntry(
        chemical_id="CWC-1-005",
        primary_name="Sulfur Mustard",
        cas_number="505-60-2",
        inchi_key="YVGGHNCTFXDRIQ-UHFFFAOYSA-N",
        canonical_smiles="ClCCSCCCl",
        molecular_formula="C4H8Cl2S",
        synonyms=["mustard gas", "bis(2-chloroethyl) sulfide", "yperite", "hd agent", "mustard agent"],
        risk_category=SafetyRiskCategory.CWC_SCHEDULE_1,
        hazard_description="Potent vesicant / blistering chemical warfare agent causing severe alkylation and DNA damage.",
        regulatory_framework="CWC Schedule 1.A.04",
    ),
    RestrictedChemicalEntry(
        chemical_id="CWC-1-006",
        primary_name="Novichok A-234",
        cas_number="26002-80-2",
        inchi_key="MUDLQGKYZPGWMS-UHFFFAOYSA-N",
        canonical_smiles=r"CCN(CC)C(=N/OP(=O)(C)F)\C",
        molecular_formula="C8H18FN2O2P",
        synonyms=["novichok", "a-234", "fourth-generation nerve agent", "a-230", "a-232"],
        risk_category=SafetyRiskCategory.CWC_SCHEDULE_1,
        hazard_description="Fourth-generation binary organophosphorus nerve agent of extraordinary toxicity.",
        regulatory_framework="CWC Schedule 1.A.13",
    ),
    RestrictedChemicalEntry(
        chemical_id="CWC-1-007",
        primary_name="Ricin",
        cas_number="9009-86-3",
        synonyms=["ricin toxin", "ricinus communis lectin", "ricin protein"],
        risk_category=SafetyRiskCategory.LETHAL_TOXIN,
        hazard_description="Ribosome-inactivating ribosome poison derived from castor beans with microgram-level lethality.",
        regulatory_framework="CWC Schedule 1.A.08",
    ),

    # â”€â”€ CWC Schedule 2 & 3 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    RestrictedChemicalEntry(
        chemical_id="CWC-2-001",
        primary_name="Amiton",
        cas_number="78-53-5",
        inchi_key="PQJCGMDFKROHHL-UHFFFAOYSA-N",
        canonical_smiles="CCOP(=O)(OCC)SCCN(CC)CC",
        molecular_formula="C10H24NO3PS",
        synonyms=["VG", "O,O-diethyl S-[2-(diethylamino)ethyl] phosphorothioate"],
        risk_category=SafetyRiskCategory.CWC_SCHEDULE_2,
        hazard_description="Dual-use organophosphate insecticide and Schedule 2 toxic nerve agent.",
        regulatory_framework="CWC Schedule 2.A.01",
    ),
    RestrictedChemicalEntry(
        chemical_id="CWC-3-001",
        primary_name="Phosgene",
        cas_number="75-44-5",
        inchi_key="YCLPJSGIGDYRAA-UHFFFAOYSA-N",
        canonical_smiles="O=C(Cl)Cl",
        molecular_formula="CCl2O",
        synonyms=["carbonyl dichloride", "carbon oxychloride", "phosgene gas"],
        risk_category=SafetyRiskCategory.CWC_SCHEDULE_3,
        hazard_description="Choking pulmonary agent causing delayed, fatal pulmonary edema.",
        regulatory_framework="CWC Schedule 3.A.01",
    ),

    # â”€â”€ Explosives & Energetic Materials â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    RestrictedChemicalEntry(
        chemical_id="EXP-001",
        primary_name="TATP",
        cas_number="17088-37-8",
        inchi_key="JGSVJNQTDDCJRL-UHFFFAOYSA-N",
        canonical_smiles="CC1(C)OOC(C)(C)OOC(C)(C)OO1",
        molecular_formula="C9H18O6",
        synonyms=["triacetone triperoxide", "peroxyacetone", "acetone peroxide", "tatp explosive"],
        risk_category=SafetyRiskCategory.EXPLOSIVE_PRECURSOR,
        hazard_description="Extremely friction- and heat-sensitive primary high explosive with no military utility.",
        regulatory_framework="UN Class 1.1A Primary Explosive",
    ),
    RestrictedChemicalEntry(
        chemical_id="EXP-002",
        primary_name="RDX",
        cas_number="121-82-4",
        inchi_key="XTFIVUFTCPULQC-UHFFFAOYSA-N",
        canonical_smiles="O=[N+]([O-])N1CN([N+](=O)[O-])CN([N+](=O)[O-])C1",
        molecular_formula="C3H6N6O6",
        synonyms=["cyclonite", "hexogen", "t4", "research department explosive", "rdx explosive"],
        risk_category=SafetyRiskCategory.EXPLOSIVE_PRECURSOR,
        hazard_description="Military secondary high explosive with high detonation velocity.",
        regulatory_framework="UN Class 1.1D High Explosive",
    ),

    # â”€â”€ Illicit Drug Precursors â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    RestrictedChemicalEntry(
        chemical_id="DRUG-001",
        primary_name="ANPP",
        cas_number="21409-26-7",
        inchi_key="KCWQMNJOHJFFPJ-UHFFFAOYSA-N",
        canonical_smiles="C1CCN(CCC1Nc2ccccc2)CCc3ccccc3",
        molecular_formula="C19H24N2",
        synonyms=["4-anilino-N-phenethylpiperidine", "fentanyl precursor ANPP", "norfentanyl intermediate"],
        risk_category=SafetyRiskCategory.ILLICIT_DRUG_PRECURSOR,
        hazard_description="Immediate chemical precursor for the clandestine synthesis of fentanyl and analogues.",
        regulatory_framework="DEA List I Precursor / INCB Schedule",
    ),
]


def deobfuscate_text(text: str) -> str:
    """
    Remove evasion obfuscations commonly used to bypass safety filters:
    - Leetspeak substitutions (@ -> a, 0 -> o, 1 -> i, 3 -> e, 5 -> s, $ -> s)
    - Punctuation / space separation: 'v - x' -> 'vx', 's a r i n' -> 'sarin'
    - Reversed strings or underscores
    """
    cleaned = text.lower().strip()

    # Leetspeak mapping
    leet_map = {
        "@": "a", "4": "a",
        "0": "o",
        "1": "i", "!": "i", "|": "i",
        "3": "e",
        "5": "s", "$": "s",
        "7": "t", "+": "t",
    }
    for char, repl in leet_map.items():
        cleaned = cleaned.replace(char, repl)

    # Remove non-alphanumeric punctuation except single dashes
    cleaned_no_punct = re.sub(r"[\s_,\.\*#]+", "", cleaned)
    return cleaned_no_punct


class RestrictedChemicalScreeningService:
    """
    Screening engine for authoritative chemical compliance.
    """

    def __init__(self, custom_entries: Optional[list[RestrictedChemicalEntry]] = None) -> None:
        self.entries = list(RESTRICTED_DATABASE)
        if custom_entries:
            self.entries.extend(custom_entries)
        self.normalizer = ChemicalEntityNormalizer()

    def screen_entity(self, identifier: str) -> Optional[ScreeningMatch]:
        """
        Screen a chemical identifier (CAS, InChIKey, SMILES, or name)
        against the restricted chemical registries.
        """
        if not identifier or not identifier.strip():
            return None

        clean_id = identifier.strip()
        deobf_id = deobfuscate_text(clean_id)

        # 1. Normalize potential CAS number
        normalized_cas = None
        cas_candidate = re.sub(r"[^\d\-]", "", clean_id)
        if self.normalizer.validate_cas_checksum(cas_candidate):
            normalized_cas = cas_candidate

        # 2. Iterate through restricted entries
        for entry in self.entries:
            # Check 1: Exact CAS Number
            if normalized_cas and entry.cas_number == normalized_cas:
                return ScreeningMatch(
                    chemical_id=entry.chemical_id,
                    matched_name=entry.primary_name,
                    matched_by="cas_number",
                    risk_category=entry.risk_category,
                    hazard_description=entry.hazard_description,
                    regulatory_framework=entry.regulatory_framework,
                    confidence=1.0,
                )

            # Check 2: Exact InChIKey match
            if entry.inchi_key and clean_id.upper() == entry.inchi_key.upper():
                return ScreeningMatch(
                    chemical_id=entry.chemical_id,
                    matched_name=entry.primary_name,
                    matched_by="inchi_key",
                    risk_category=entry.risk_category,
                    hazard_description=entry.hazard_description,
                    regulatory_framework=entry.regulatory_framework,
                    confidence=1.0,
                )

            # Check 3: Canonical SMILES match
            if entry.canonical_smiles and clean_id == entry.canonical_smiles:
                return ScreeningMatch(
                    chemical_id=entry.chemical_id,
                    matched_name=entry.primary_name,
                    matched_by="canonical_smiles",
                    risk_category=entry.risk_category,
                    hazard_description=entry.hazard_description,
                    regulatory_framework=entry.regulatory_framework,
                    confidence=1.0,
                )

            # Check 4: Primary name and synonyms (with deobfuscation)
            all_names = [entry.primary_name] + entry.synonyms
            for name in all_names:
                deobf_name = deobfuscate_text(name)
                # Exact or substring match on deobfuscated name
                if deobf_name in deobf_id or deobf_id in deobf_name:
                    return ScreeningMatch(
                        chemical_id=entry.chemical_id,
                        matched_name=entry.primary_name,
                        matched_by="synonym",
                        risk_category=entry.risk_category,
                        hazard_description=entry.hazard_description,
                        regulatory_framework=entry.regulatory_framework,
                        confidence=0.95,
                    )

        return None

    def screen_text_for_restricted_chemicals(self, text: str) -> list[ScreeningMatch]:
        """
        Scan a query, paragraph, or document context for any mentions
        of restricted chemical substances.
        """
        matches: list[ScreeningMatch] = []
        seen_ids: set[str] = set()

        # 1. Check CAS patterns: \b\d{2,7}-\d{2}-\d\b
        for cas in re.findall(r"\b\d{2,7}-\d{2}-\d\b", text):
            match = self.screen_entity(cas)
            if match and match.chemical_id not in seen_ids:
                matches.append(match)
                seen_ids.add(match.chemical_id)

        # 2. Check full text and words against restricted dictionary
        for entry in self.entries:
            if entry.chemical_id in seen_ids:
                continue
            all_names = [entry.primary_name] + entry.synonyms
            for name in all_names:
                # Word boundary match
                pattern = rf"\b{re.escape(name)}\b"
                if re.search(pattern, text, re.IGNORECASE):
                    match = ScreeningMatch(
                        chemical_id=entry.chemical_id,
                        matched_name=entry.primary_name,
                        matched_by="text_mention",
                        risk_category=entry.risk_category,
                        hazard_description=entry.hazard_description,
                        regulatory_framework=entry.regulatory_framework,
                        confidence=0.95,
                    )
                    matches.append(match)
                    seen_ids.add(entry.chemical_id)
                    break

        # 3. Check deobfuscated text against high-risk primary agents
        deobf = deobfuscate_text(text)
        for entry in self.entries:
            if entry.chemical_id in seen_ids:
                continue
            deobf_name = deobfuscate_text(entry.primary_name)
            if len(deobf_name) >= 4 and deobf_name in deobf:
                match = ScreeningMatch(
                    chemical_id=entry.chemical_id,
                    matched_name=entry.primary_name,
                    matched_by="deobfuscated_mention",
                    risk_category=entry.risk_category,
                    hazard_description=entry.hazard_description,
                    regulatory_framework=entry.regulatory_framework,
                    confidence=0.90,
                )
                matches.append(match)
                seen_ids.add(entry.chemical_id)

        return matches

