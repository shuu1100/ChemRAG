"""
ChemRAG — Multi-Agent Graph State
===================================
Fulfills Phase 11 / Prompt 11.1:
Strongly typed LangGraph state containing query, conversation ID, tenant ID,
intent, subtasks, retrieval queries, retrieved/reranked chunks, chemical entities,
tool calls, safety decision, answer, citations, confidence, and errors.
"""
from __future__ import annotations

import enum
from typing import Any, List, Optional, TypedDict
import uuid
from pydantic import BaseModel, Field

from backend.app.retrieval.models import ScoredChunk


class QuestionIntent(str, enum.Enum):
    FACTOID = "factoid"
    CHEMICAL_IDENTITY = "chemical_identity"
    CHEMICAL_PROPERTY = "chemical_property"
    REACTION_SYNTHESIS = "reaction_synthesis"
    CALCULATION_ANALYTICS = "calculation_analytics"
    COMPARISON = "comparison"
    SAFETY_HAZARD = "safety_hazard"
    GENERAL = "general"


class SubTaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SubTask(BaseModel):
    """Decomposed unit of work planned by the Planner Agent."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str
    target_agent: str  # "retrieval" | "chemistry" | "analytics" | "aggregator"
    status: SubTaskStatus = SubTaskStatus.PENDING
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class ToolCallRecord(BaseModel):
    """Structured record of tool invocation (Prompt 2.1 / Prompt 11.1)."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str
    input_args: dict[str, Any] = Field(default_factory=dict)
    output_result: Any = None
    execution_time_ms: float = 0.0
    status: str = "success"  # "success" | "error"
    error_message: Optional[str] = None


class CitationData(BaseModel):
    """Citation back to source document, page, and bounding box."""
    document_id: str
    chunk_id: str
    page_number: Optional[int] = None
    snippet: str
    score: float = 0.0
    title: Optional[str] = None
    bbox: Optional[dict[str, float]] = None


class ContradictionRecord(BaseModel):
    """Detected conflict between multiple retrieved sources."""
    topic: str
    source_a: str
    source_b: str
    conflict_description: str
    severity: str = "warning"  # "info" | "warning" | "high"


class SafetyDecision(BaseModel):
    """Safety evaluation for dangerous chemistry queries."""
    is_safe: bool = True
    reason: Optional[str] = None
    hazard_flags: list[str] = Field(default_factory=list)
    restricted_action_prevented: bool = False


class ChemicalEntityData(BaseModel):
    """Normalized chemical entity recognized or verified during execution."""
    name: Optional[str] = None
    smiles: Optional[str] = None
    canonical_smiles: Optional[str] = None
    inchi: Optional[str] = None
    inchi_key: Optional[str] = None
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    cas_number: Optional[str] = None
    properties: dict[str, Any] = Field(default_factory=dict)
    source: str = "query"  # "query" | "retrieval" | "pubchem"


class CalculationRecord(BaseModel):
    """Transparent calculation result from Analytics Agent."""
    calculation_type: str
    inputs: dict[str, Any]
    formula_applied: str
    result_value: Any
    units: str
    assumptions: list[str] = Field(default_factory=list)


class AgentState(TypedDict, total=False):
    """
    Strongly typed LangGraph GraphState (Prompt 11.1).
    Used as state dict in StateGraph.
    """
    query: str
    conversation_id: str
    tenant_id: str
    intent: QuestionIntent
    subtasks: list[SubTask]
    current_subtask_index: int
    retrieval_queries: list[str]
    retrieved_chunks: list[ScoredChunk]
    reranked_chunks: list[ScoredChunk]
    chemical_entities: list[ChemicalEntityData]
    calculation_results: list[CalculationRecord]
    tool_calls: list[ToolCallRecord]
    safety_decision: Optional[SafetyDecision]
    answer: Optional[str]
    citations: list[CitationData]
    contradictions: list[ContradictionRecord]
    confidence: float
    errors: list[str]
    # Internal scratchpad for audit (NEVER exposed in UI, Prompt 11.6 Exit Criteria)
    internal_scratchpad: list[str]
