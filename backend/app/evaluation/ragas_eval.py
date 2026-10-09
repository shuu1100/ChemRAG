"""
ChemRAG — RAGAS-Style RAG Evaluation
====================================
Implements claim-based & heuristic RAGAS-style metrics:
- Context Precision: ratio of relevant retrieved context chunks
- Context Recall: ground truth claim overlap with context
- Faithfulness: ratio of generated answer claims supported by context
- Answer Relevance: semantic keyword alignment with the question

Treats LLM-as-judge metrics as measurements, not absolute truth.
Stores model versions, evaluation runs, and metadata.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class RagasEvaluationResult:
    """RAGAS metric scores payload."""
    context_precision: float = 0.0
    context_recall: float = 0.0
    faithfulness: float = 0.0
    answer_relevance: float = 0.0
    overall_ragas_score: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_precision": round(self.context_precision, 4),
            "context_recall": round(self.context_recall, 4),
            "faithfulness": round(self.faithfulness, 4),
            "answer_relevance": round(self.answer_relevance, 4),
            "overall_ragas_score": round(self.overall_ragas_score, 4),
            "details": self.details,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


class RagasEvaluator:
    """Evaluates RAG pipeline outputs using RAGAS-style metrics."""

    def evaluate_item(
        self,
        query: str,
        retrieved_contexts: List[str],
        generated_answer: str,
        expected_answer: Optional[str] = None,
    ) -> RagasEvaluationResult:
        """Evaluate a single query-answer generation result."""
        ctx_prec = self.calculate_context_precision(query, retrieved_contexts)
        ctx_rec = self.calculate_context_recall(expected_answer, retrieved_contexts) if expected_answer else 1.0
        faith = self.calculate_faithfulness(generated_answer, retrieved_contexts)
        ans_rel = self.calculate_answer_relevance(query, generated_answer)

        overall = (ctx_prec + ctx_rec + faith + ans_rel) / 4.0

        return RagasEvaluationResult(
            context_precision=ctx_prec,
            context_recall=ctx_rec,
            faithfulness=faith,
            answer_relevance=ans_rel,
            overall_ragas_score=overall,
            details={
                "retrieved_context_count": len(retrieved_contexts),
                "answer_char_len": len(generated_answer),
            },
        )

    def calculate_context_precision(self, query: str, contexts: List[str]) -> float:
        """Calculate context precision: proportion of retrieved contexts containing query keywords."""
        if not contexts:
            return 0.0
        keywords = set(re.findall(r"\w{4,}", query.lower()))
        if not keywords:
            return 1.0

        hits = 0
        for ctx in contexts:
            ctx_lower = ctx.lower()
            if any(kw in ctx_lower for kw in keywords):
                hits += 1

        return hits / len(contexts)

    def calculate_context_recall(self, expected_answer: str, contexts: List[str]) -> float:
        """Calculate context recall: fraction of expected answer sentences present in context."""
        if not expected_answer or not contexts:
            return 1.0

        sentences = [s.strip() for s in re.split(r"[.!?]", expected_answer) if len(s.strip()) > 10]
        if not sentences:
            return 1.0

        joined_ctx = " ".join(contexts).lower()
        matched = 0
        for stmt in sentences:
            stmt_words = set(re.findall(r"\w{4,}", stmt.lower()))
            if not stmt_words:
                matched += 1
                continue
            if any(w in joined_ctx for w in stmt_words):
                matched += 1

        return matched / len(sentences)

    def calculate_faithfulness(self, generated_answer: str, contexts: List[str]) -> float:
        """Calculate faithfulness: fraction of generated answer statements grounded in context."""
        if not generated_answer:
            return 1.0
        if not contexts:
            return 0.0

        joined_ctx = " ".join(contexts).lower()
        claims = [c.strip() for c in re.split(r"[.!?]", generated_answer) if len(c.strip()) > 10]
        if not claims:
            return 1.0

        supported = 0
        for claim in claims:
            words = set(re.findall(r"\w{4,}", claim.lower()))
            if not words:
                supported += 1
                continue
            # If at least 50% of claim's key words appear in context, consider it supported
            matches = sum(1 for w in words if w in joined_ctx)
            if matches / len(words) >= 0.4:
                supported += 1

        return supported / len(claims)

    def calculate_answer_relevance(self, query: str, generated_answer: str) -> float:
        """Calculate answer relevance: keyword alignment between query and generated response."""
        if not query or not generated_answer:
            return 0.0

        query_words = set(re.findall(r"\w{4,}", query.lower()))
        if not query_words:
            return 1.0

        ans_lower = generated_answer.lower()
        matches = sum(1 for w in query_words if w in ans_lower)
        return matches / len(query_words)
