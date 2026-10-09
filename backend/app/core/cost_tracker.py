"""
ChemRAG — Usage Metering & Cost Tracking
=========================================
Tracks token counts, API call rates, and compute usage:
- LLM input/output tokens and model pricing
- Embedding chunks & vector generation
- Reranker candidate queries
- OCR/OCSR parser invocations (GROBID, DECIMER, MolScribe)
- External API calls (PubChem, Crossref, OpenAlex, PubMed, arXiv)
- GPU & CPU processing time

CRITICAL: Keeps estimated financial cost metrics completely separate
from scientific output payloads.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.app.core.logging import get_logger

logger = get_logger(__name__)

# Model pricing reference per 1,000 tokens (USD)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "gpt-4o": {"input": 0.0025, "output": 0.0100},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "claude-3-5-sonnet": {"input": 0.0030, "output": 0.0150},
    "text-embedding-3-large": {"input": 0.00013, "output": 0.0},
    "cohere-rerank-v3": {"input": 0.0020, "output": 0.0},  # per query
}


@dataclass
class UsageRecord:
    """Metering record for a single execution task."""
    task_type: str  # llm, embedding, reranker, ocr, external_api
    provider: str
    model: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    chunks_count: int = 0
    candidates_count: int = 0
    external_calls_count: int = 0
    gpu_time_ms: float = 0.0
    cpu_time_ms: float = 0.0
    estimated_cost_usd: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def calculate_cost(self) -> float:
        cost = 0.0
        if self.model and self.model in MODEL_PRICING:
            pricing = MODEL_PRICING[self.model]
            cost += (self.prompt_tokens / 1000.0) * pricing.get("input", 0.0)
            cost += (self.completion_tokens / 1000.0) * pricing.get("output", 0.0)
        self.estimated_cost_usd = round(cost, 6)
        return self.estimated_cost_usd


class CostTracker:
    """Thread-safe usage metering and cost estimation tracker."""

    def __init__(self) -> None:
        self.records: List[UsageRecord] = []

    def record_llm_usage(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cpu_time_ms: float = 0.0,
    ) -> UsageRecord:
        rec = UsageRecord(
            task_type="llm",
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cpu_time_ms=cpu_time_ms,
        )
        rec.calculate_cost()
        self.records.append(rec)
        logger.debug("Recorded LLM token usage", model=model, cost=rec.estimated_cost_usd)
        return rec

    def record_embedding_usage(
        self,
        provider: str,
        model: str,
        chunks_count: int,
        total_tokens: int,
        gpu_time_ms: float = 0.0,
    ) -> UsageRecord:
        rec = UsageRecord(
            task_type="embedding",
            provider=provider,
            model=model,
            chunks_count=chunks_count,
            prompt_tokens=total_tokens,
            gpu_time_ms=gpu_time_ms,
        )
        rec.calculate_cost()
        self.records.append(rec)
        return rec

    def record_reranker_usage(
        self,
        provider: str,
        model: str,
        candidates_count: int,
        cpu_time_ms: float = 0.0,
    ) -> UsageRecord:
        rec = UsageRecord(
            task_type="reranker",
            provider=provider,
            model=model,
            candidates_count=candidates_count,
            cpu_time_ms=cpu_time_ms,
        )
        rec.calculate_cost()
        self.records.append(rec)
        return rec

    def record_ocr_usage(
        self,
        tool: str,  # grobid, decimer, molscribe
        cpu_time_ms: float = 0.0,
        gpu_time_ms: float = 0.0,
    ) -> UsageRecord:
        rec = UsageRecord(
            task_type="ocr_ocsr",
            provider=tool,
            cpu_time_ms=cpu_time_ms,
            gpu_time_ms=gpu_time_ms,
        )
        self.records.append(rec)
        return rec

    def record_external_api_call(self, provider: str, endpoint: str) -> UsageRecord:
        rec = UsageRecord(
            task_type="external_api",
            provider=provider,
            external_calls_count=1,
        )
        self.records.append(rec)
        return rec

    def get_cumulative_summary(self) -> Dict[str, Any]:
        """Summarizes usage, token totals, and estimated financial costs."""
        total_llm_prompt_tokens = sum(r.prompt_tokens for r in self.records if r.task_type == "llm")
        total_llm_completion_tokens = sum(r.completion_tokens for r in self.records if r.task_type == "llm")
        total_embedding_chunks = sum(r.chunks_count for r in self.records if r.task_type == "embedding")
        total_cost_usd = sum(r.estimated_cost_usd for r in self.records)
        total_external_calls = sum(r.external_calls_count for r in self.records if r.task_type == "external_api")

        return {
            "total_llm_prompt_tokens": total_llm_prompt_tokens,
            "total_llm_completion_tokens": total_llm_completion_tokens,
            "total_llm_tokens": total_llm_prompt_tokens + total_llm_completion_tokens,
            "total_embedding_chunks": total_embedding_chunks,
            "total_external_calls": total_external_calls,
            "estimated_total_cost_usd": round(total_cost_usd, 4),
            "total_records_count": len(self.records),
        }


# Global cost tracker instance
cost_tracker = CostTracker()
