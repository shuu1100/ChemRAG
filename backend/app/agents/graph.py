"""
ChemRAG — LangGraph Multi-Agent Orchestrator Graph
===================================================
Fulfills Phase 11 / Prompt 11.1 - 11.6 & Exit Criteria:
- Explicit nodes: planner, retrieval, chemistry, analytics, aggregator.
- Explicit conditional transitions.
- Controlled tool invocation interfaces.
- Safe execution: strips internal scratchpad from UI answers.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional, cast

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.aggregator import AggregatorAgent
from backend.app.agents.analytics_agent import AnalyticsAgent
from backend.app.agents.chemistry_agent import ChemistryAgent
from backend.app.agents.planner import PlannerAgent
from backend.app.agents.retrieval_agent import RetrievalAgent
from backend.app.agents.state import AgentState, SafetyDecision, SubTaskStatus
from backend.app.core.logging import get_logger
from backend.app.safety.guard import SafetyToolGuard
from backend.app.safety.models import SafetyViolationError

logger = get_logger(__name__)


def route_next_step(state: AgentState) -> str:
    """
    Conditional routing function based on pending subtasks.
    Routes to 'chemistry', 'retrieval', 'analytics', or 'aggregator'.
    """
    # 1. If safety restriction was triggered, go straight to aggregator
    safety = state.get("safety_decision")
    if safety and not safety.is_safe:
        return "aggregator"

    # 2. Look for the next pending subtask
    subtasks = state.get("subtasks", [])
    for st in subtasks:
        if st.status == SubTaskStatus.PENDING:
            if st.target_agent in ["chemistry", "retrieval", "analytics"]:
                return st.target_agent
            elif st.target_agent == "aggregator":
                return "aggregator"

    # All worker subtasks finished -> aggregator
    return "aggregator"


class ChemRAGAgentGraph:
    """
    Stateful multi-agent system orchestrator compiled with LangGraph.
    """

    def __init__(
        self,
        planner: Optional[PlannerAgent] = None,
        retrieval: Optional[RetrievalAgent] = None,
        chemistry: Optional[ChemistryAgent] = None,
        analytics: Optional[AnalyticsAgent] = None,
        aggregator: Optional[AggregatorAgent] = None,
        guard: Optional[SafetyToolGuard] = None,
        session: Optional[AsyncSession] = None,
    ) -> None:
        self.planner = planner or PlannerAgent()
        self.retrieval = retrieval or RetrievalAgent()
        self.chemistry = chemistry or ChemistryAgent()
        self.analytics = analytics or AnalyticsAgent()
        self.aggregator = aggregator or AggregatorAgent()
        self.guard = guard or SafetyToolGuard()
        self.session = session
        self.logger = logger

        # Build and compile LangGraph
        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        """Construct the explicit StateGraph and transitions."""
        builder = StateGraph(AgentState)  # type: ignore[arg-type]

        # 1. Register explicit nodes
        builder.add_node("planner", self._node_planner)
        builder.add_node("retrieval", self._node_retrieval)
        builder.add_node("chemistry", self._node_chemistry)
        builder.add_node("analytics", self._node_analytics)
        builder.add_node("aggregator", self._node_aggregator)

        # 2. Connect START -> planner
        builder.add_edge(START, "planner")

        # 3. Connect planner -> conditional route
        builder.add_conditional_edges(
            "planner",
            route_next_step,
            {
                "retrieval": "retrieval",
                "chemistry": "chemistry",
                "analytics": "analytics",
                "aggregator": "aggregator",
            },
        )

        # 4. Connect worker nodes back to conditional router
        for worker in ["retrieval", "chemistry", "analytics"]:
            builder.add_conditional_edges(
                worker,
                route_next_step,
                {
                    "retrieval": "retrieval",
                    "chemistry": "chemistry",
                    "analytics": "analytics",
                    "aggregator": "aggregator",
                },
            )

        # 5. Connect aggregator -> END
        builder.add_edge("aggregator", END)

        return builder.compile()

    # Node execution handlers
    async def _node_planner(self, state: AgentState) -> AgentState:
        return await self.planner.run(state)

    async def _node_retrieval(self, state: AgentState) -> AgentState:
        return await self.retrieval.run(state, session=self.session)

    async def _node_chemistry(self, state: AgentState) -> AgentState:
        try:
            res = await self.guard.guard_call(
                self.chemistry.run,
                "chemistry_reasoning_and_validation",
                state,
                session=self.session,
            )
            return cast(AgentState, res)
        except SafetyViolationError as exc:
            scratchpad = list(state.get("internal_scratchpad", []))
            scratchpad.append(f"[SafetyGuard] Chemistry tool call blocked: {exc}")
            return cast(AgentState, {
                **state,
                "safety_decision": SafetyDecision(
                    is_safe=False,
                    reason=exc.evaluation.reason,
                    hazard_flags=exc.evaluation.hazard_flags,
                    restricted_action_prevented=True,
                ),
                "internal_scratchpad": scratchpad,
            })

    async def _node_analytics(self, state: AgentState) -> AgentState:
        return await self.analytics.run(state)

    async def _node_aggregator(self, state: AgentState) -> AgentState:
        return await self.aggregator.run(state)

    async def run(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> AgentState:
        """
        Execute the agent graph for a user query.
        Returns the finalized AgentState.
        """
        if session is not None:
            self.session = session

        initial_state: AgentState = {
            "query": query,
            "conversation_id": conversation_id or str(uuid.uuid4()),
            "tenant_id": tenant_id or "default-tenant",
            "subtasks": [],
            "current_subtask_index": 0,
            "retrieval_queries": [],
            "retrieved_chunks": [],
            "reranked_chunks": [],
            "chemical_entities": [],
            "calculation_results": [],
            "tool_calls": [],
            "safety_decision": None,
            "answer": None,
            "citations": [],
            "contradictions": [],
            "confidence": 0.0,
            "errors": [],
            "internal_scratchpad": [],
        }

        # Invoke the compiled LangGraph workflow asynchronously
        result = await self.graph.ainvoke(initial_state)
        return cast(AgentState, result)
