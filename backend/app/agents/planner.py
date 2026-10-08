"""
ChemRAG — Planner Agent
=========================
Fulfills Phase 11 / Prompt 11.2:
- Classifies questions into chemical domain intents.
- Identifies evidence needs (retrieval, chemical validation, calculations).
- Decomposes complex questions into ordered subtasks with routing.
- Constrained: Never executes arbitrary code.
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Optional

from backend.app.agents.state import (
    AgentState,
    QuestionIntent,
    SafetyDecision,
    SubTask,
    SubTaskStatus,
)
from backend.app.core.logging import get_logger
from backend.app.safety.models import PolicyDecision
from backend.app.safety.policy_engine import SafetyPolicyEngine

logger = get_logger(__name__)

# Hazardous keywords indicative of restricted chemical agent queries (CBRN / explosives / illicit drugs)
RESTRICTED_KEYWORDS = [
    "sarin", "soman", "tabun", "vx nerve", "novichok",
    "mustard gas", "phosgene synthesis", "ricin extraction",
    "weaponize", "clandestine explosive", "rdx synthesis",
    "tatp synthesis", "c4 explosive", "improvised explosive",
    "heroin synthesis", "methamphetamine cook", "fentanyl clandestine",
]

# Calculation indicators
CALCULATION_KEYWORDS = [
    "calculate", "yield", "molar", "moles", "concentration", "molarity",
    "molecular weight", "stoichiometry", "limiting reagent", "dilution",
    "convert", "mass", "grams", "mg", "ml", "standard deviation", "mean",
]

# Chemical property / structure indicators
CHEMICAL_KEYWORDS = [
    "smiles", "inchi", "cas", "structure", "formula", "logp", "tpsa",
    "molecular formula", "iupac", "pubchem", "isomer", "chirality",
    "functional group", "melting point", "boiling point",
]


class PlannerAgent:
    """
    Constrained Planner Agent for chemical domain workflows.
    Decomposes queries into controlled subtasks without executing arbitrary code.
    """

    def __init__(self, safety_engine: Optional[SafetyPolicyEngine] = None) -> None:
        self.safety_engine = safety_engine or SafetyPolicyEngine()
        self.logger = logger

    def classify_intent(self, query: str) -> QuestionIntent:
        """Classify question intent based on domain patterns."""
        q_lower = query.lower()

        # 1. Safety check
        if any(kw in q_lower for kw in RESTRICTED_KEYWORDS):
            return QuestionIntent.SAFETY_HAZARD

        # 2. Calculation / Analytics
        if any(kw in q_lower for kw in CALCULATION_KEYWORDS) and any(
            unit in q_lower for unit in ["mol", "g", "mg", "ml", "l", "%", "yield", "molar", "ppm"]
        ):
            return QuestionIntent.CALCULATION_ANALYTICS

        # 3. Chemical Identity / Property
        if any(kw in q_lower for kw in ["smiles", "structure of", "inchi", "cas number"]):
            return QuestionIntent.CHEMICAL_IDENTITY

        if any(kw in q_lower for kw in ["solubility", "boiling point", "melting point", "tpsa", "logp", "pka"]):
            return QuestionIntent.CHEMICAL_PROPERTY

        # 4. Reaction / Synthesis
        if any(kw in q_lower for kw in ["synthesis", "reaction", "reagent", "catalyst", "mechanism", "procedure"]):
            return QuestionIntent.REACTION_SYNTHESIS

        # 5. Comparison
        if any(kw in q_lower for kw in ["compare", "difference between", "versus", "vs.", "better yield"]):
            return QuestionIntent.COMPARISON

        # Default: Factoid or General
        if any(q_lower.startswith(w) for w in ["what is", "who", "when", "define", "name"]):
            return QuestionIntent.FACTOID

        return QuestionIntent.GENERAL

    def assess_evidence_needs(self, query: str, intent: QuestionIntent) -> dict[str, bool]:
        """Determine what components are needed to fulfill the request."""
        q_lower = query.lower()

        needs_retrieval = intent in [
            QuestionIntent.FACTOID,
            QuestionIntent.CHEMICAL_PROPERTY,
            QuestionIntent.REACTION_SYNTHESIS,
            QuestionIntent.COMPARISON,
            QuestionIntent.GENERAL,
        ] or "document" in q_lower or "paper" in q_lower or "study" in q_lower

        needs_chemical_validation = intent in [
            QuestionIntent.CHEMICAL_IDENTITY,
            QuestionIntent.CHEMICAL_PROPERTY,
            QuestionIntent.REACTION_SYNTHESIS,
        ] or any(kw in q_lower for kw in CHEMICAL_KEYWORDS)

        needs_calculation = intent == QuestionIntent.CALCULATION_ANALYTICS or any(
            kw in q_lower for kw in ["calculate", "how many moles", "percent yield", "dilute", "molarity"]
        )

        is_restricted = intent == QuestionIntent.SAFETY_HAZARD

        return {
            "needs_retrieval": needs_retrieval,
            "needs_chemical_validation": needs_chemical_validation,
            "needs_calculation": needs_calculation,
            "is_restricted": is_restricted,
        }

    def decompose(self, query: str, intent: QuestionIntent, needs: dict[str, bool]) -> list[SubTask]:
        """
        Decomposes query into an ordered sequence of safe subtasks.
        Never outputs arbitrary code execution tasks.
        """
        subtasks: list[SubTask] = []

        # If safety hazard, route immediately to safety decision
        if needs["is_restricted"]:
            subtasks.append(
                SubTask(
                    description=f"Evaluate safety hazard for restricted chemical query: {query}",
                    target_agent="aggregator",
                    input_data={"safety_flag": True},
                )
            )
            return subtasks

        # 1. Chemical validation subtask (if chemical entities or SMILES are in query)
        if needs["needs_chemical_validation"]:
            subtasks.append(
                SubTask(
                    description="Validate chemical identifiers, SMILES, and extract molecular properties",
                    target_agent="chemistry",
                    input_data={"query": query},
                )
            )

        # 2. Retrieval subtask (if document evidence is required)
        if needs["needs_retrieval"]:
            subtasks.append(
                SubTask(
                    description="Execute multi-modal hybrid retrieval and cross-encoder reranking across document corpus",
                    target_agent="retrieval",
                    input_data={"query": query},
                )
            )

        # 3. Calculation subtask (if numerical or stoichiometric math is requested)
        if needs["needs_calculation"]:
            subtasks.append(
                SubTask(
                    description="Perform deterministic chemical / mathematical analytics calculation",
                    target_agent="analytics",
                    input_data={"query": query},
                )
            )

        # 4. Aggregator subtask (always the final synthesis step)
        subtasks.append(
            SubTask(
                description="Synthesize evidence, detect contradictions, link citations, and assemble response",
                target_agent="aggregator",
                input_data={"query": query},
            )
        )

        return subtasks

    async def run(self, state: AgentState) -> AgentState:
        """Execute planner node within the LangGraph graph."""
        query = state.get("query", "")
        scratchpad = list(state.get("internal_scratchpad", []))

        scratchpad.append(f"[Planner] Analyzing query: '{query}'")

        # 1. Classify intent
        intent = self.classify_intent(query)
        scratchpad.append(f"[Planner] Classified intent: {intent.value}")

        # 2. Check safety / evidence needs
        needs = self.assess_evidence_needs(query, intent)
        scratchpad.append(
            f"[Planner] Evidence needs: retrieval={needs['needs_retrieval']}, "
            f"chem={needs['needs_chemical_validation']}, calc={needs['needs_calculation']}, "
            f"restricted={needs['is_restricted']}"
        )

        # 3. Policy Engine Evaluation (Phase 12 Safety Integration)
        policy_res = self.safety_engine.evaluate(
            query=query,
            requested_action="query",
            query_intent=intent.value,
        )

        safety_dec = None
        if not policy_res.is_allowed:
            needs["is_restricted"] = True
            safety_dec = SafetyDecision(
                is_safe=False,
                reason=policy_res.reason,
                hazard_flags=policy_res.hazard_flags,
                restricted_action_prevented=True,
            )
            scratchpad.append(f"[Planner] SAFETY POLICY ENFORCEMENT: {policy_res.reason} (Rules: {policy_res.matched_rules})")
        elif needs["is_restricted"]:
            safety_dec = SafetyDecision(
                is_safe=False,
                reason="Query contains restricted hazardous chemical synthesis or dangerous substance directives.",
                hazard_flags=["prohibited_synthesis", "cbrn_threat"],
                restricted_action_prevented=True,
            )
            scratchpad.append("[Planner] SAFETY RESTRICTION ACTIVATED: Prohibited query blocked.")

        # 4. Decompose into subtasks
        subtasks = self.decompose(query, intent, needs)
        scratchpad.append(f"[Planner] Planned {len(subtasks)} subtasks: {[st.target_agent for st in subtasks]}")

        # Return updated state
        return {
            **state,
            "intent": intent,
            "subtasks": subtasks,
            "current_subtask_index": 0,
            "safety_decision": safety_dec,
            "internal_scratchpad": scratchpad,
        }
