"""
ChemRAG — Configurable Chemical Safety Policy Engine
=====================================================
Fulfills Phase 12 / Prompt 12.1:
- Evaluates:
  * Normalized chemical entities
  * Requested action (synthesis, query, property_lookup, autonomous_execution)
  * Document context (retrieved chunks, parsed sources)
  * User role (GUEST, STUDENT, RESEARCHER, COMPLIANCE_OFFICER, ADMIN)
  * Query intent (FACTOID, REACTION_SYNTHESIS, etc.)
- Returns:
  * ALLOW
  * ALLOW_WITH_WARNING
  * REQUIRE_REVIEW
  * REFUSE
- Stores policy rules in an external JSON configuration file.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from backend.app.core.logging import get_logger
from backend.app.safety.injection_detector import InjectionDetectionService
from backend.app.safety.models import (
    PolicyDecision,
    PolicyRule,
    RestrictedChemicalEntry,
    SafetyEvaluationResult,
    SafetyRiskCategory,
    ScreeningMatch,
    UserRole,
)
from backend.app.safety.restricted_chemicals import RestrictedChemicalScreeningService

logger = get_logger(__name__)

# Default external policy configuration rules
DEFAULT_POLICY_RULES: list[dict[str, Any]] = [
    {
        "rule_id": "RULE-001-INJECTION",
        "name": "Prompt and Tool Injection Defense",
        "description": "Block any adversarial prompt overrides, jailbreaks, or arbitrary code execution.",
        "action_pattern": "all",
        "risk_categories": ["prompt_injection"],
        "minimum_role": "admin",
        "default_decision": "REFUSE",
        "warning_message": "Prompt injection attempt blocked.",
        "policy_version": "1.0.0",
        "is_active": True,
    },
    {
        "rule_id": "RULE-002-AUTONOMOUS",
        "name": "Prohibit Autonomous Laboratory Execution",
        "description": "Strictly prohibit unmonitored robotic synthesis or automated physical lab execution.",
        "action_pattern": "autonomous_execution",
        "risk_categories": ["autonomous_execution"],
        "minimum_role": "admin",
        "default_decision": "REFUSE",
        "warning_message": "Autonomous lab control directives are prohibited by safety policy.",
        "policy_version": "1.0.0",
        "is_active": True,
    },
    {
        "rule_id": "RULE-003-CWC1",
        "name": "Absolute Prohibition on Schedule 1 Chemical Weapons",
        "description": "Zero-tolerance refusal for Chemical Weapons Convention Schedule 1 synthesis, handling, or dissemination.",
        "action_pattern": "synthesis",
        "risk_categories": ["cwc_schedule_1", "lethal_toxin"],
        "minimum_role": "admin",
        "default_decision": "REFUSE",
        "warning_message": "CWC Schedule 1 chemical weapons synthesis or manufacture is strictly prohibited.",
        "policy_version": "1.0.0",
        "is_active": True,
    },
    {
        "rule_id": "RULE-004-EXPLOSIVES",
        "name": "Explosives and Energetics Restriction",
        "description": "Prohibit improvised explosive synthesis and energetic precursor preparation.",
        "action_pattern": "synthesis",
        "risk_categories": ["explosive_precursor"],
        "minimum_role": "compliance_officer",
        "default_decision": "REFUSE",
        "warning_message": "High-explosive and energetic material synthesis instructions are blocked.",
        "policy_version": "1.0.0",
        "is_active": True,
    },
    {
        "rule_id": "RULE-005-DRUG-PRECURSORS",
        "name": "Illicit Controlled Substance Precursor Safeguard",
        "description": "Refuse clandestine synthesis instructions for controlled narcotic precursors.",
        "action_pattern": "synthesis",
        "risk_categories": ["illicit_drug_precursor"],
        "minimum_role": "compliance_officer",
        "default_decision": "REFUSE",
        "warning_message": "Illicit substance precursor synthesis is restricted.",
        "policy_version": "1.0.0",
        "is_active": True,
    },
    {
        "rule_id": "RULE-006-DUAL-USE-LOOKUP",
        "name": "Dual-Use Educational Property Access",
        "description": "Allow factual toxicity/physical property lookups for dual-use Schedule 2/3 chemicals with mandatory hazard warnings.",
        "action_pattern": "property_lookup",
        "risk_categories": ["cwc_schedule_2", "cwc_schedule_3"],
        "minimum_role": "student",
        "default_decision": "ALLOW_WITH_WARNING",
        "warning_message": "Chemical is subject to dual-use regulatory oversight. Observe international handling precautions.",
        "policy_version": "1.0.0",
        "is_active": True,
    },
    {
        "rule_id": "RULE-007-RESEARCHER-REVIEW",
        "name": "Dual-Use Synthesis Academic Review",
        "description": "Require compliance review before providing industrial reaction pathways for Schedule 2 dual-use substances.",
        "action_pattern": "synthesis",
        "risk_categories": ["cwc_schedule_2", "cwc_schedule_3"],
        "minimum_role": "researcher",
        "default_decision": "REQUIRE_REVIEW",
        "warning_message": "Action requires Institutional Review Board (IRB) or Compliance Officer approval.",
        "policy_version": "1.0.0",
        "is_active": True,
    },
]


class SafetyPolicyEngine:
    """
    Dedicated, non-bypassable policy engine for chemistry tool execution.
    """

    def __init__(
        self,
        rules_path: Optional[str] = None,
        screening_service: Optional[RestrictedChemicalScreeningService] = None,
        injection_service: Optional[InjectionDetectionService] = None,
    ) -> None:
        self.screening_service = screening_service or RestrictedChemicalScreeningService()
        self.injection_service = injection_service or InjectionDetectionService()
        self.rules_path = Path(rules_path) if rules_path else None
        self.rules: list[PolicyRule] = self._load_rules()
        self.policy_version = "1.0.0"

    def _load_rules(self) -> list[PolicyRule]:
        """Load external policy rules from JSON or fallback to defaults."""
        raw_list = DEFAULT_POLICY_RULES

        if self.rules_path and self.rules_path.exists():
            try:
                with open(self.rules_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        raw_list = data
            except Exception as e:
                logger.warning("Failed loading external safety rules from %s: %s", self.rules_path, e)

        rules: list[PolicyRule] = []
        for r in raw_list:
            try:
                rules.append(
                    PolicyRule(
                        rule_id=r["rule_id"],
                        name=r["name"],
                        description=r["description"],
                        action_pattern=r["action_pattern"],
                        risk_categories=[SafetyRiskCategory(c) for c in r.get("risk_categories", [])],
                        minimum_role=UserRole(r.get("minimum_role", "researcher")),
                        default_decision=PolicyDecision(r.get("default_decision", "REFUSE")),
                        warning_message=r.get("warning_message"),
                        policy_version=r.get("policy_version", "1.0.0"),
                        is_active=r.get("is_active", True),
                    )
                )
            except Exception as exc:
                logger.debug("Skipping invalid rule definition: %s", exc)

        return rules

    def save_rules_to_file(self, target_path: str) -> None:
        """Persist current rules to an external JSON configuration file."""
        p = Path(target_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        serializable = [r.model_dump() for r in self.rules]
        with open(p, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2)

    def evaluate(
        self,
        query: str,
        entities: Optional[list[str]] = None,
        requested_action: str = "query",
        document_context: Optional[str] = None,
        user_role: UserRole = UserRole.RESEARCHER,
        query_intent: Optional[str] = None,
    ) -> SafetyEvaluationResult:
        """
        Evaluate full chemical safety and compliance policy.
        Returns explicit decision: ALLOW, ALLOW_WITH_WARNING, REQUIRE_REVIEW, or REFUSE.
        """
        matched_rules: list[str] = []
        matches: list[ScreeningMatch] = []
        hazard_flags: list[str] = []
        warnings: list[str] = []

        # 1. Prompt Injection and Adversarial Manipulation Defense (Prompt 12.3)
        is_inj, inj_reason = self.injection_service.detect_prompt_injection(query)
        if is_inj:
            return SafetyEvaluationResult(
                decision=PolicyDecision.REFUSE,
                reason=f"Adversarial prompt injection rejected: {inj_reason}",
                matched_rules=["RULE-001-INJECTION"],
                hazard_flags=["prompt_injection_threat"],
                user_role=user_role,
                requested_action=requested_action,
                policy_version=self.policy_version,
            )

        # 2. Tool Injection Defense
        is_tool, tool_reason = self.injection_service.detect_tool_injection(query)
        if is_tool:
            return SafetyEvaluationResult(
                decision=PolicyDecision.REFUSE,
                reason=f"Unauthorized tool/code execution pattern blocked: {tool_reason}",
                matched_rules=["RULE-001-INJECTION"],
                hazard_flags=["tool_injection_threat"],
                user_role=user_role,
                requested_action=requested_action,
                policy_version=self.policy_version,
            )

        # 3. Document Context Indirect Prompt Injection Defense
        if document_context:
            is_doc_inj, doc_inj_reason = self.injection_service.screen_document_content(document_context)
            if is_doc_inj:
                return SafetyEvaluationResult(
                    decision=PolicyDecision.REFUSE,
                    reason=f"Document contains malicious indirect injection payload: {doc_inj_reason}",
                    matched_rules=["RULE-001-INJECTION"],
                    hazard_flags=["malicious_document_injection"],
                    user_role=user_role,
                    requested_action=requested_action,
                    policy_version=self.policy_version,
                )

        # 4. Autonomous Laboratory Execution Guard
        if requested_action in ["autonomous_execution", "robotic_synthesis", "lab_execution"]:
            return SafetyEvaluationResult(
                decision=PolicyDecision.REFUSE,
                reason="Autonomous or robotic laboratory synthesis execution is strictly prohibited.",
                matched_rules=["RULE-002-AUTONOMOUS"],
                hazard_flags=["prohibited_autonomous_execution"],
                user_role=user_role,
                requested_action=requested_action,
                policy_version=self.policy_version,
            )

        # 5. Chemical Entity Screening across Query, Provided Entities, and Document Context
        screening_texts = [query]
        if entities:
            screening_texts.extend(entities)
        if document_context:
            screening_texts.append(document_context)

        for text in screening_texts:
            found = self.screening_service.screen_text_for_restricted_chemicals(text)
            for m in found:
                if m.chemical_id not in [x.chemical_id for x in matches]:
                    matches.append(m)
                    hazard_flags.append(f"{m.risk_category.value}:{m.matched_name}")

        # If no restricted chemicals matched, evaluate requested action
        if not matches:
            return SafetyEvaluationResult(
                decision=PolicyDecision.ALLOW,
                reason="No restricted substances or safety policy violations detected.",
                user_role=user_role,
                requested_action=requested_action,
                policy_version=self.policy_version,
            )

        # 6. Apply Policy Rules Against Matched Chemical Entities
        highest_severity_decision = PolicyDecision.ALLOW

        # Determine if action involves synthesis/preparation
        _synthesis_action_names = {
            "synthesis", "reaction_synthesis", "preparation", "manufacturing",
            "chemistry_synthesis", "chemistry_reasoning_and_validation",
        }
        is_synthesis_action = requested_action in _synthesis_action_names
        if query_intent in ["reaction_synthesis"]:
            is_synthesis_action = True

        # Detect synthesis intent directly from query text
        _SYNTHESIS_TEXT_PATTERNS = [
            "how to make", "synthesize", "synthesis route", "provide synthesis",
            "procedure", "step by step", "make ", "produce ", "manufacture",
            "preparation of", "clandestine", "precursor",
        ]
        query_lower = query.lower()
        has_synthesis_text = any(p in query_lower for p in _SYNTHESIS_TEXT_PATTERNS)

        for m in matches:
            # Schedule 1 or lethal toxin: Always REFUSE — these chemicals have no legitimate
            # synthesis use case in any user-facing research system.
            if m.risk_category in [SafetyRiskCategory.CWC_SCHEDULE_1, SafetyRiskCategory.LETHAL_TOXIN]:
                if is_synthesis_action or has_synthesis_text or "nerve agent" in query_lower or "chemical weapon" in query_lower:
                    return SafetyEvaluationResult(
                        decision=PolicyDecision.REFUSE,
                        reason=f"Action involves restricted CWC Schedule 1 chemical / lethal toxin: '{m.matched_name}'. Synthesis directives are strictly refused.",
                        matched_rules=["RULE-003-CWC1"],
                        matches=matches,
                        hazard_flags=hazard_flags,
                        user_role=user_role,
                        requested_action=requested_action,
                        policy_version=self.policy_version,
                    )
                # If merely looking up historical/factoid information:
                warnings.append(f"Subject molecule '{m.matched_name}' is classified under {m.regulatory_framework}.")
                matched_rules.append("RULE-003-CWC1")
                highest_severity_decision = self._escalate_decision(highest_severity_decision, PolicyDecision.ALLOW_WITH_WARNING)

            # Explosive Precursor:
            elif m.risk_category == SafetyRiskCategory.EXPLOSIVE_PRECURSOR:
                if is_synthesis_action or has_synthesis_text or "make" in query_lower:
                    return SafetyEvaluationResult(
                        decision=PolicyDecision.REFUSE,
                        reason=f"Action involves explosive precursor '{m.matched_name}'. Energetic material manufacturing is prohibited.",
                        matched_rules=["RULE-004-EXPLOSIVES"],
                        matches=matches,
                        hazard_flags=hazard_flags,
                        user_role=user_role,
                        requested_action=requested_action,
                        policy_version=self.policy_version,
                    )
                warnings.append(f"Precursor '{m.matched_name}' is subject to explosive precursor regulations.")
                matched_rules.append("RULE-004-EXPLOSIVES")
                highest_severity_decision = self._escalate_decision(highest_severity_decision, PolicyDecision.ALLOW_WITH_WARNING)

            # Illicit Drug Precursor:
            elif m.risk_category == SafetyRiskCategory.ILLICIT_DRUG_PRECURSOR:
                if is_synthesis_action:
                    return SafetyEvaluationResult(
                        decision=PolicyDecision.REFUSE,
                        reason=f"Action involves controlled drug precursor '{m.matched_name}'. Clandestine synthesis directives are refused.",
                        matched_rules=["RULE-005-DRUG-PRECURSORS"],
                        matches=matches,
                        hazard_flags=hazard_flags,
                        user_role=user_role,
                        requested_action=requested_action,
                        policy_version=self.policy_version,
                    )
                warnings.append(f"Entity '{m.matched_name}' is regulated under controlled precursor frameworks.")
                matched_rules.append("RULE-005-DRUG-PRECURSORS")
                highest_severity_decision = self._escalate_decision(highest_severity_decision, PolicyDecision.ALLOW_WITH_WARNING)

            # Schedule 2 / 3 Dual-Use Chemicals:
            elif m.risk_category in [SafetyRiskCategory.CWC_SCHEDULE_2, SafetyRiskCategory.CWC_SCHEDULE_3]:
                if is_synthesis_action:
                    if user_role in [UserRole.GUEST, UserRole.STUDENT]:
                        return SafetyEvaluationResult(
                            decision=PolicyDecision.REFUSE,
                            reason=f"Synthesis procedures for dual-use substance '{m.matched_name}' require researcher credentials.",
                            matched_rules=["RULE-007-RESEARCHER-REVIEW"],
                            matches=matches,
                            hazard_flags=hazard_flags,
                            user_role=user_role,
                            requested_action=requested_action,
                            policy_version=self.policy_version,
                        )
                    else:
                        matched_rules.append("RULE-007-RESEARCHER-REVIEW")
                        highest_severity_decision = self._escalate_decision(highest_severity_decision, PolicyDecision.REQUIRE_REVIEW)
                        warnings.append(f"Dual-use industrial synthesis for '{m.matched_name}' requires institutional review.")
                else:
                    matched_rules.append("RULE-006-DUAL-USE-LOOKUP")
                    warnings.append(f"Dual-use substance '{m.matched_name}' is governed by {m.regulatory_framework}.")
                    highest_severity_decision = self._escalate_decision(highest_severity_decision, PolicyDecision.ALLOW_WITH_WARNING)

        return SafetyEvaluationResult(
            decision=highest_severity_decision,
            reason=f"Safety evaluation complete: {highest_severity_decision.value}",
            matched_rules=matched_rules,
            matches=matches,
            hazard_flags=hazard_flags,
            warnings=warnings,
            user_role=user_role,
            requested_action=requested_action,
            policy_version=self.policy_version,
        )

    def _escalate_decision(self, current: PolicyDecision, candidate: PolicyDecision) -> PolicyDecision:
        """Helper to retain the most restrictive policy decision."""
        severity_order = [
            PolicyDecision.ALLOW,
            PolicyDecision.ALLOW_WITH_WARNING,
            PolicyDecision.REQUIRE_REVIEW,
            PolicyDecision.REFUSE,
        ]
        curr_idx = severity_order.index(current)
        cand_idx = severity_order.index(candidate)
        return severity_order[max(curr_idx, cand_idx)]
