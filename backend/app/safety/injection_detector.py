"""
ChemRAG — Prompt Injection & Adversarial Evasion Detector
==========================================================
Fulfills Phase 12 / Prompt 12.3:
- Detects system prompt overriding attempts ("ignore previous instructions", "jailbreak").
- Detects tool injection attempts (shell access, code execution, environment reading).
- Detects attempts to manipulate safety policy decisions (e.g. fake user_role injection).
- Detects indirect prompt injection embedded within parsed documents or retrieved chunks.
"""
from __future__ import annotations

import base64
import re
from typing import Optional

from backend.app.safety.models import SafetyRiskCategory

# Direct Prompt Injection Patterns
INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+)?(?:previous|prior)\s+(?:instructions|rules|prompts|constraints)",
    r"disregard\s+(?:all\s+)?(?:safety|system|compliance)\s+(?:rules|policies|guidelines)",
    r"you\s+are\s+now\s+(?:unrestricted|in\s+developer\s+mode|dan\s+mode|jailbroken)",
    r"bypass\s+(?:all\s+)?(?:safety|policy|security|guardrails|checks)",
    r"system\s*:\s*you\s+must\s+comply",
    r"override\s+(?:policy|filter|safety\s+guard)",
    r"pretend\s+(?:there\s+are\s+no\s+rules|you\s+have\s+no\s+ethics)",
    r"disable\s+(?:safety|content\s+filter|guardrails)",
]

# Tool Injection & Code Execution Patterns
TOOL_INJECTION_PATTERNS = [
    r"\b(?:exec|eval|__import__|subprocess|os\.system|shutil)\b",
    r"\b(?:bash|powershell|cmd\.exe|/bin/sh)\b",
    r"\b(?:cat\s+/etc/passwd|type\s+c:\\windows)\b",
    r"invoke_tool\s*\(",
    r"call_tool\s*\(",
    r"DROP\s+TABLE|SELECT\s+\*\s+FROM\s+users|--\s*$",
]

# Policy Decision Manipulation Patterns (attempts to trick the safety engine)
POLICY_SPOOF_PATTERNS = [
    r"user_role\s*[:=]\s*['\"]?admin['\"]?",
    r"safety_decision\s*[:=]\s*['\"]?ALLOW['\"]?",
    r"override_role\s*[:=]",
    r"authorization\s*[:=]\s*['\"]?super_user['\"]?",
]


class InjectionDetectionService:
    """
    Dedicated analyzer for adversarial prompt injection and tool manipulation.
    """

    def detect_prompt_injection(self, text: str) -> tuple[bool, Optional[str]]:
        """
        Scan input text for adversarial prompt injection patterns.
        Returns (is_injection, reason).
        """
        if not text:
            return False, None

        # 1. Check direct prompt injection regex
        for pattern in INJECTION_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return True, f"Detected direct prompt injection pattern: '{match.group(0)}'"

        # 2. Check base64-encoded payload hiding injection
        base64_strings = re.findall(r"\b[A-Za-z0-9+/]{20,}={0,2}\b", text)
        for b64 in base64_strings:
            try:
                decoded = base64.b64decode(b64).decode("utf-8", errors="ignore")
                for pattern in INJECTION_PATTERNS:
                    if re.search(pattern, decoded, re.IGNORECASE):
                        return True, "Detected base64-obfuscated prompt injection payload"
            except Exception:
                pass

        # 3. Check for policy spoofing attempts
        for pattern in POLICY_SPOOF_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return True, f"Detected safety policy spoofing attempt: '{match.group(0)}'"

        return False, None

    def detect_tool_injection(self, text: str) -> tuple[bool, Optional[str]]:
        """
        Scan input text for tool / shell execution manipulation.
        Returns (is_tool_injection, reason).
        """
        if not text:
            return False, None

        for pattern in TOOL_INJECTION_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return True, f"Detected unauthorized code/tool execution pattern: '{match.group(0)}'"

        return False, None

    def screen_document_content(self, document_text: str) -> tuple[bool, Optional[str]]:
        """
        Detect indirect prompt injection embedded within parsed PDF documents.
        """
        is_inj, reason = self.detect_prompt_injection(document_text)
        if is_inj:
            return True, f"Indirect document injection detected: {reason}"

        is_tool, reason = self.detect_tool_injection(document_text)
        if is_tool:
            return True, f"Malicious executable payload in document: {reason}"

        return False, None
