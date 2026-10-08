"""
ChemRAG — Safety and Compliance Package
=========================================
Covers:
- Policy engine with external rules
- Authoritative restricted chemical dataset screening
- Non-bypassable tool guard and injection detector
"""
from backend.app.safety.guard import SafetyToolGuard, guarded_tool
from backend.app.safety.injection_detector import InjectionDetectionService
from backend.app.safety.models import (
    PolicyDecision,
    PolicyRule,
    RestrictedChemicalEntry,
    SafetyEvaluationResult,
    SafetyRiskCategory,
    SafetyViolationError,
    ScreeningMatch,
    UserRole,
)
from backend.app.safety.policy_engine import SafetyPolicyEngine
from backend.app.safety.restricted_chemicals import (
    RESTRICTED_DATABASE,
    RestrictedChemicalScreeningService,
    deobfuscate_text,
)

__all__ = [
    "PolicyDecision",
    "SafetyRiskCategory",
    "UserRole",
    "RestrictedChemicalEntry",
    "ScreeningMatch",
    "PolicyRule",
    "SafetyEvaluationResult",
    "SafetyViolationError",
    "RestrictedChemicalScreeningService",
    "RESTRICTED_DATABASE",
    "deobfuscate_text",
    "InjectionDetectionService",
    "SafetyPolicyEngine",
    "SafetyToolGuard",
    "guarded_tool",
]
