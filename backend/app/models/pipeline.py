"""
ChemRAG — Pipeline Job & Agent State Models
=============================================
Covers: ingestion_jobs, retrieval_queries, retrieval_results,
        agent_runs, tool_calls, safety_events,
        evaluation_runs, evaluation_cases, audit_logs
"""
from __future__ import annotations

import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Enum as SAEnum, Float, ForeignKey,
    Index, Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import Any, TYPE_CHECKING

from backend.app.db.base import Base
from backend.app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from backend.app.models.document import ProcessingState

if TYPE_CHECKING:
    from backend.app.models.document import Document


# ─────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────


class AgentRunState(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SafetyDecision(str, enum.Enum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    FLAGGED = "flagged"
    REDACTED = "redacted"


class AuditAction(str, enum.Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    QUERY = "query"
    UPLOAD = "upload"
    EXPORT = "export"


# ─────────────────────────────────────────────────────────
# Ingestion Jobs
# ─────────────────────────────────────────────────────────


class IngestionJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks the full ingestion pipeline for a document.
    Each phase (parse, chunk, embed) updates state and progress.
    """
    __tablename__ = "ingestion_jobs"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
    )
    state: Mapped[ProcessingState] = mapped_column(
        SAEnum(ProcessingState, name="processing_state_enum"), nullable=False,
        default=ProcessingState.PENDING, index=True,
    )
    current_phase: Mapped[str | None] = mapped_column(String(64), nullable=True)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0)
    celery_task_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_traceback: Mapped[str | None] = mapped_column(Text, nullable=True)
    phase_timings: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)  # {phase: seconds}
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    document: Mapped["Document"] = relationship("Document", back_populates="ingestion_jobs")  # type: ignore[name-defined]


# ─────────────────────────────────────────────────────────
# Retrieval & Search
# ─────────────────────────────────────────────────────────


class RetrievalQuery(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Records every search/retrieval request for observability and evaluation."""
    __tablename__ = "retrieval_queries"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    query_embedding_model: Mapped[str | None] = mapped_column(String(256), nullable=True)
    filters: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    strategy: Mapped[str | None] = mapped_column(String(64), nullable=True)  # hybrid, dense, sparse
    top_k: Mapped[int] = mapped_column(Integer, default=10)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_count: Mapped[int] = mapped_column(Integer, default=0)

    results: Mapped[list["RetrievalResult"]] = relationship(
        "RetrievalResult", back_populates="query",
    )
    agent_run: Mapped["AgentRun | None"] = relationship(
        "AgentRun", back_populates="retrieval_queries",
    )



class RetrievalResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Individual ranked result returned for a retrieval query."""
    __tablename__ = "retrieval_results"

    query_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("retrieval_queries.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    vector_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    bm25_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rerank_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    was_used_in_answer: Mapped[bool] = mapped_column(Boolean, default=False)
    user_feedback: Mapped[int | None] = mapped_column(Integer, nullable=True)  # -1, 0, 1

    query: Mapped["RetrievalQuery"] = relationship("RetrievalQuery", back_populates="results")


# ─────────────────────────────────────────────────────────
# Agent Runs & Tool Calls
# ─────────────────────────────────────────────────────────


class AgentRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Single execution of the LangGraph agent pipeline.
    Stores the full conversation state and graph execution trace.
    """
    __tablename__ = "agent_runs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    state: Mapped[AgentRunState] = mapped_column(
        SAEnum(AgentRunState, name="agent_run_state_enum"), nullable=False,
        default=AgentRunState.PENDING, index=True,
    )
    # Input
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    query_filters: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # Output
    final_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_citations: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    # Graph execution state (for LangGraph checkpointing)
    graph_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    langgraph_thread_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    # Metrics
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    tool_calls: Mapped[list["ToolCall"]] = relationship("ToolCall", back_populates="agent_run")
    retrieval_queries: Mapped[list["RetrievalQuery"]] = relationship(
        "RetrievalQuery", back_populates="agent_run",
        primaryjoin="AgentRun.id == foreign(RetrievalQuery.agent_run_id)",
    )
    safety_events: Mapped[list["SafetyEvent"]] = relationship(
        "SafetyEvent", back_populates="agent_run",
    )


class ToolCall(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Individual tool invocation within an AgentRun."""
    __tablename__ = "tool_calls"

    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    call_index: Mapped[int] = mapped_column(Integer, default=0)
    input_args: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)

    agent_run: Mapped["AgentRun"] = relationship("AgentRun", back_populates="tool_calls")


# ─────────────────────────────────────────────────────────
# Safety Events
# ─────────────────────────────────────────────────────────


class SafetyEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Audit record for every safety check decision.
    Provides full trail for regulatory compliance review.
    """
    __tablename__ = "safety_events"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    decision: Mapped[SafetyDecision] = mapped_column(
        SAEnum(SafetyDecision, name="safety_decision_enum"), nullable=False, index=True,
    )
    check_type: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    input_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    flagged_content: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    agent_run: Mapped["AgentRun | None"] = relationship("AgentRun", back_populates="safety_events")


# ─────────────────────────────────────────────────────────
# Evaluation
# ─────────────────────────────────────────────────────────


class EvaluationRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A batch evaluation run against a test dataset."""
    __tablename__ = "evaluation_runs"

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    dataset_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    state: Mapped[ProcessingState] = mapped_column(
        SAEnum(ProcessingState, name="processing_state_enum"), nullable=False,
        default=ProcessingState.PENDING,
    )
    metrics_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    case_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    cases: Mapped[list["EvaluationCase"]] = relationship("EvaluationCase", back_populates="run")


class EvaluationCase(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Single question-answer-context evaluation case."""
    __tablename__ = "evaluation_cases"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    ground_truth: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_contexts: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    faithfulness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    answer_relevancy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    context_precision_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    context_recall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped["EvaluationRun"] = relationship("EvaluationRun", back_populates="cases")


# ─────────────────────────────────────────────────────────
# Audit Log
# ─────────────────────────────────────────────────────────


class AuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Immutable audit trail for all state-changing actions.
    Never updated or deleted (append-only by policy).
    """
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_org_action", "organization_id", "action"),
        Index("ix_audit_user_created", "user_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    action: Mapped[AuditAction] = mapped_column(
        SAEnum(AuditAction, name="audit_action_enum"), nullable=False, index=True,
    )
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv6 max
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
