"""
ChemRAG — Aggregator Agent
===========================
Fulfills Phase 11 / Prompt 11.6:
- Synthesizes evidence across retrieval, chemistry, and analytics subtasks.
- Distinguishes direct document evidence from algorithmic inference.
- Attaches granular citations with page and chunk references.
- Detects contradictions across sources and highlights them transparently.
- States uncertainty explicitly when evidence is incomplete.
- Never silently resolves conflicting sources.
- Exit Criteria: Strips internal reasoning/scratchpad so no hidden chain-of-thought
  is exposed in the user-facing answer.
"""
from __future__ import annotations

import re
import time
from typing import Any, List, Optional

from backend.app.agents.state import (
    AgentState,
    CitationData,
    ContradictionRecord,
    ToolCallRecord,
)
from backend.app.core.logging import get_logger

logger = get_logger(__name__)


class AggregatorAgent:
    """
    Evidence-grounded Aggregator and Answer Synthesis Agent.
    Combines retrieved evidence, chemical properties, and analytics results
    into a structured, cited answer with contradiction detection.
    """

    def __init__(self) -> None:
        self.logger = logger

    def detect_contradictions(self, state: AgentState) -> list[ContradictionRecord]:
        """
        Scan retrieved chunks for conflicting empirical values
        (e.g., conflicting melting points, conflicting yield percentages, contradictory procedures).
        """
        contradictions: list[ContradictionRecord] = []
        chunks = state.get("retrieved_chunks", [])
        if len(chunks) < 2:
            return contradictions

        # Scan for conflicting yield percentages: e.g. "yield of 85%" vs "yield of 62%"
        yield_pattern = re.compile(r"(?:yield|conversion)\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*%", re.IGNORECASE)
        found_yields: list[tuple[float, str, str]] = []  # (value, doc_id, snippet)

        for c in chunks:
            matches = yield_pattern.findall(c.content)
            for m in matches:
                val = float(m)
                found_yields.append((val, str(c.document_id)[:8], c.content[:100]))

        if len(found_yields) >= 2:
            # Check if there is a divergence > 10%
            vals = [y[0] for y in found_yields]
            if max(vals) - min(vals) > 10.0:
                contradictions.append(
                    ContradictionRecord(
                        topic="Reaction Yield Discrepancy",
                        source_a=f"Source [{found_yields[0][1]}]: {found_yields[0][0]}% ({found_yields[0][2]}...)",
                        source_b=f"Source [{found_yields[-1][1]}]: {found_yields[-1][0]}% ({found_yields[-1][2]}...)",
                        conflict_description=(
                            f"Multiple documents report significantly diverging yields: "
                            f"{min(vals):.1f}% vs {max(vals):.1f}%. "
                            "Variation may be due to differing catalysts, reaction scales, or reaction times."
                        ),
                        severity="warning",
                    )
                )

        return contradictions

    def format_citations(self, citations: list[CitationData]) -> str:
        """Format bibliographic citations for user display."""
        if not citations:
            return ""

        lines = ["\n### References & Citations:"]
        for idx, cit in enumerate(citations[:5], start=1):
            page_str = f"Page {cit.page_number}" if cit.page_number else "Page N/A"
            lines.append(f"[{idx}] Document `{cit.document_id[:8]}...`, {page_str}: \"{cit.snippet.strip()}...\" (Score: {cit.score:.3f})")
        return "\n".join(lines)

    def assemble_answer(
        self,
        state: AgentState,
        contradictions: list[ContradictionRecord],
    ) -> str:
        """
        Synthesize clean, evidence-based answer without exposing chain-of-thought.
        """
        query = state.get("query", "")
        chunks = state.get("retrieved_chunks", [])
        chem_entities = state.get("chemical_entities", [])
        calcs = state.get("calculation_results", [])
        safety_dec = state.get("safety_decision")

        # 1. Safety Blocked Answer
        if safety_dec and not safety_dec.is_safe:
            return (
                f"**Request Restricted by Chemical Safety Policy**\n\n"
                f"{safety_dec.reason}\n\n"
                f"ChemRAG strictly prevents assistance with the synthesis, optimization, or weaponization "
                f"of restricted chemical agents, explosives, or illicit substances."
            )

        sections: list[str] = []

        # 2. Direct Findings / Evidence Synthesis
        sections.append(f"### Chemical Research Analysis for: \"{query}\"\n")

        # Chemical Entities section (if characterized)
        if chem_entities:
            sections.append("#### Chemical Entities & Molecular Properties:")
            for ent in chem_entities:
                name_str = ent.name or "Chemical Compound"
                formula_str = f" | Formula: `{ent.molecular_formula}`" if ent.molecular_formula else ""
                mw_str = f" | MW: `{ent.molecular_weight:.2f} g/mol`" if ent.molecular_weight else ""
                smiles_str = f"\n  - Canonical SMILES: `{ent.canonical_smiles or ent.smiles}`" if (ent.canonical_smiles or ent.smiles) else ""
                inchi_str = f"\n  - InChIKey: `{ent.inchi_key}`" if ent.inchi_key else ""
                cas_str = f"\n  - CAS Registry Number: `{ent.cas_number}`" if ent.cas_number else ""

                props_list = []
                for k, v in ent.properties.items():
                    if k not in ["synonyms", "cid"]:
                        props_list.append(f"{k.replace('_', ' ').title()}: {v}")
                props_str = f"\n  - Computed Descriptors: {', '.join(props_list)}" if props_list else ""

                sections.append(f"- **{name_str}**{formula_str}{mw_str}{smiles_str}{inchi_str}{cas_str}{props_str}")
            sections.append("")

        # Calculations section (if analytics were performed)
        if calcs:
            sections.append("#### Analytical & Stoichiometric Calculations:")
            for calc in calcs:
                sections.append(f"- **{calc.calculation_type.replace('_', ' ').title()}**:")
                sections.append(f"  - Formula Applied: `{calc.formula_applied}`")
                sections.append(f"  - Calculated Result: **{calc.result_value} {calc.units}**")
                if calc.assumptions:
                    sections.append(f"  - Assumptions: {'; '.join(calc.assumptions)}")
            sections.append("")

        # Document Evidence Passages
        if chunks:
            sections.append("#### Evidence Grounding:")
            for idx, c in enumerate(chunks[:3], start=1):
                page_str = f" (Page {c.page_number})" if c.page_number else ""
                sections.append(f"**Evidence [{idx}]**{page_str}:\n> {c.content.strip()}\n")
        else:
            if not calcs and not chem_entities:
                sections.append("No direct document evidence was found matching the query criteria in the indexed corpus.")

        # Contradictions / Conflict Reporting
        if contradictions:
            sections.append("#### Discrepancies & Conflicting Sources:")
            for contra in contradictions:
                sections.append(f"> [!WARNING]\n> **{contra.topic}**\n> {contra.conflict_description}\n> - {contra.source_a}\n> - {contra.source_b}\n")

        # Uncertainty Statement
        if not chunks and not chem_entities and not calcs:
            sections.append("\n*Uncertainty note: Confidence is low due to absence of corroborating scientific evidence.*")

        # Citations
        citations_str = self.format_citations(state.get("citations", []))
        if citations_str:
            sections.append(citations_str)

        return "\n".join(sections)

    async def run(self, state: AgentState) -> AgentState:
        """Run aggregator node in the LangGraph graph."""
        scratchpad = list(state.get("internal_scratchpad", []))
        tool_calls = list(state.get("tool_calls", []))

        t0 = time.perf_counter()
        scratchpad.append("[AggregatorAgent] Synthesizing final answer from evidence")

        # 1. Detect source contradictions
        contradictions = self.detect_contradictions(state)
        if contradictions:
            scratchpad.append(f"[AggregatorAgent] Detected {len(contradictions)} conflicting sources")

        # 2. Assemble clean response (without scratchpad)
        answer = self.assemble_answer(state, contradictions)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # Calculate overall confidence
        confidence = 0.5
        if state.get("safety_decision") and not state["safety_decision"].is_safe:
            confidence = 1.0
        elif state.get("retrieved_chunks"):
            confidence = min(1.0, 0.6 + len(state["retrieved_chunks"]) * 0.08)
        elif state.get("calculation_results") or state.get("chemical_entities"):
            confidence = 0.85

        tool_calls.append(
            ToolCallRecord(
                tool_name="aggregate_evidence_synthesis",
                input_args={"chunks_count": len(state.get("retrieved_chunks", []))},
                output_result="Generated synthesized response and citations",
                execution_time_ms=round(elapsed_ms, 2),
                status="success",
            )
        )

        scratchpad.append(f"[AggregatorAgent] Final response generated (Confidence: {confidence:.2f}, {elapsed_ms:.1f}ms)")

        # Mark subtask completed
        subtasks = list(state.get("subtasks", []))
        for st in subtasks:
            if st.target_agent == "aggregator":
                st.status = "completed"

        return {
            **state,
            "answer": answer,
            "contradictions": contradictions,
            "confidence": round(confidence, 2),
            "tool_calls": tool_calls,
            "subtasks": subtasks,
            "internal_scratchpad": scratchpad,
        }
