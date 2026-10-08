"""
ChemRAG — Non-Bypassable Safety Tool Guard
===========================================
Fulfills Phase 12 / Prompt 12.3 & Exit Criteria:
- Enforces: Agent → Safety Guard → Policy Decision → Tool.
- Intercepts every chemistry tool call before execution.
- Prevents tool execution if decision is REFUSE or REQUIRE_REVIEW.
- Logs every safety decision to audit trails and the database.
- Completely immune to agent prompt override or prompt injection.
"""
from __future__ import annotations

import functools
import inspect
import time
from typing import Any, Callable, Coroutine, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import get_logger
from backend.app.models.pipeline import SafetyDecision as DBSafetyDecision, SafetyEvent
from backend.app.safety.models import (
    PolicyDecision,
    SafetyEvaluationResult,
    SafetyViolationError,
    UserRole,
)
from backend.app.safety.policy_engine import SafetyPolicyEngine

logger = get_logger(__name__)


class SafetyToolGuard:
    """
    Non-bypassable enforcement barrier for agent tool invocations.
    """

    def __init__(self, policy_engine: Optional[SafetyPolicyEngine] = None) -> None:
        self.policy_engine = policy_engine or SafetyPolicyEngine()
        self.audit_log: list[SafetyEvaluationResult] = []
        self.logger = logger

    async def log_safety_event_to_db(
        self,
        evaluation: SafetyEvaluationResult,
        session: Optional[AsyncSession] = None,
        organization_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        agent_run_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Persist safety decision record to database safety_events table."""
        # Always store in in-memory audit log
        self.audit_log.append(evaluation)

        if session is not None:
            try:
                # Map PolicyDecision to DB SafetyDecision enum
                db_decision = DBSafetyDecision.ALLOWED
                if evaluation.decision == PolicyDecision.REFUSE:
                    db_decision = DBSafetyDecision.BLOCKED
                elif evaluation.decision in (PolicyDecision.ALLOW_WITH_WARNING, PolicyDecision.REQUIRE_REVIEW):
                    db_decision = DBSafetyDecision.FLAGGED

                org_id = organization_id or uuid.uuid4()
                evt = SafetyEvent(
                    id=uuid.UUID(evaluation.event_id),
                    organization_id=org_id,
                    user_id=user_id,
                    agent_run_id=agent_run_id,
                    decision=db_decision,
                    check_type=f"tool_guard:{evaluation.requested_action}",
                    confidence=1.0,
                    input_text=evaluation.requested_action,
                    reasoning=evaluation.reason,
                    flagged_content=evaluation.hazard_flags or None,
                )
                session.add(evt)
                await session.flush()
            except Exception as exc:
                self.logger.warning("Failed logging safety event to database: %s", exc)

    async def guard_call(
        self,
        func: Callable[..., Any],
        action_name: str,
        *args: Any,
        user_role: UserRole = UserRole.RESEARCHER,
        document_context: Optional[str] = None,
        session: Optional[AsyncSession] = None,
        organization_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        agent_run_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Execute tool through safety guard barrier:
        Agent → Safety Guard → Policy Decision → Tool.
        """
        # 1. Extract query/text from arguments
        extracted_text = ""
        entities_list: list[str] = []

        def _extract_from_dict(d: dict) -> None:
            """Recursively pull string values from a dict into extracted_text and entities_list."""
            nonlocal extracted_text
            for k, v in d.items():
                if isinstance(v, str):
                    extracted_text += " " + v
                    if k in ["query", "smiles", "chemical_name", "cas", "identifier", "chemical", "name"]:
                        entities_list.append(v)
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, str):
                            extracted_text += " " + item
                            entities_list.append(item)

        for arg in args:
            if isinstance(arg, str):
                extracted_text += " " + arg
            elif isinstance(arg, list):
                for item in arg:
                    if isinstance(item, str):
                        extracted_text += " " + item
                        entities_list.append(item)
            elif isinstance(arg, dict):
                _extract_from_dict(arg)

        for k, v in kwargs.items():
            if isinstance(v, str):
                extracted_text += " " + v
                if k in ["query", "smiles", "chemical_name", "cas", "identifier", "chemical", "name"]:
                    entities_list.append(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, str):
                        extracted_text += " " + item
                        entities_list.append(item)
            elif isinstance(v, dict):
                _extract_from_dict(v)

        extracted_text = extracted_text.strip() or action_name

        # 2. Evaluate Policy
        evaluation = self.policy_engine.evaluate(
            query=extracted_text,
            entities=entities_list if entities_list else None,
            requested_action=action_name,
            document_context=document_context,
            user_role=user_role,
        )

        # 3. Log event
        await self.log_safety_event_to_db(
            evaluation=evaluation,
            session=session,
            organization_id=organization_id,
            user_id=user_id,
            agent_run_id=agent_run_id,
        )

        # 4. Enforce decision: REFUSE
        if evaluation.decision == PolicyDecision.REFUSE:
            self.logger.warning(
                "SAFETY GUARD REFUSED TOOL CALL: action=%s, reason=%s, rules=%s",
                action_name,
                evaluation.reason,
                evaluation.matched_rules,
            )
            raise SafetyViolationError(evaluation)

        # 5. Enforce decision: REQUIRE_REVIEW
        if evaluation.decision == PolicyDecision.REQUIRE_REVIEW:
            self.logger.warning(
                "SAFETY GUARD REQUIRES HUMAN REVIEW: action=%s, rules=%s",
                action_name,
                evaluation.matched_rules,
            )
            raise SafetyViolationError(evaluation)

        # 6. Execute Tool (Async or Sync)
        if inspect.iscoroutinefunction(func):
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)

        # 7. Attach warnings if ALLOW_WITH_WARNING
        if evaluation.decision == PolicyDecision.ALLOW_WITH_WARNING and evaluation.warnings:
            if isinstance(result, dict):
                result["_safety_warnings"] = evaluation.warnings
                result["_safety_decision"] = evaluation.decision.value

        return result


def guarded_tool(action_name: str, guard: Optional[SafetyToolGuard] = None):
    """
    Decorator to wrap chemistry tools with non-bypassable Safety Guard.
    Usage:
        @guarded_tool("chemical_synthesis")
        async def synthesize_compound(compound_name: str, ...):
            ...
    """
    active_guard = guard or SafetyToolGuard()

    def decorator(fn: Callable[..., Any]):
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any):
            user_role = kwargs.pop("user_role", UserRole.RESEARCHER)
            doc_ctx = kwargs.pop("document_context", None)
            session = kwargs.pop("session", None)
            return await active_guard.guard_call(
                fn,
                action_name,
                *args,
                user_role=user_role,
                document_context=doc_ctx,
                session=session,
                **kwargs,
            )

        return wrapper

    return decorator
