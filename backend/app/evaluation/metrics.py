"""
ChemRAG — Retrieval Metrics Calculator
=======================================
Implements quantitative retrieval metrics:
- Recall@1/5/10/20
- MRR (Mean Reciprocal Rank)
- nDCG@K (Normalized Discounted Cumulative Gain)
- Precision@K (Precision@1/5/10)
- Latency percentiles (P50, P95, P99)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Set, Union


@dataclass
class RetrievalMetricsResult:
    """Quantitative evaluation metrics container."""
    recall_at_1: float = 0.0
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    recall_at_20: float = 0.0
    precision_at_1: float = 0.0
    precision_at_5: float = 0.0
    precision_at_10: float = 0.0
    mrr: float = 0.0
    ndcg_at_5: float = 0.0
    ndcg_at_10: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    total_queries: int = 0

    def to_dict(self) -> Dict[str, float]:
        return {
            "recall_at_1": round(self.recall_at_1, 4),
            "recall_at_5": round(self.recall_at_5, 4),
            "recall_at_10": round(self.recall_at_10, 4),
            "recall_at_20": round(self.recall_at_20, 4),
            "precision_at_1": round(self.precision_at_1, 4),
            "precision_at_5": round(self.precision_at_5, 4),
            "precision_at_10": round(self.precision_at_10, 4),
            "mrr": round(self.mrr, 4),
            "ndcg_at_5": round(self.ndcg_at_5, 4),
            "ndcg_at_10": round(self.ndcg_at_10, 4),
            "latency_p50_ms": round(self.latency_p50_ms, 2),
            "latency_p95_ms": round(self.latency_p95_ms, 2),
            "latency_p99_ms": round(self.latency_p99_ms, 2),
            "total_queries": self.total_queries,
        }


def recall_at_k(retrieved_ids: Sequence[str], expected_ids: Sequence[str], k: int) -> float:
    """Calculate Recall@K: fraction of expected relevant items present in top-K."""
    if not expected_ids:
        return 1.0
    top_k_set = set(retrieved_ids[:k])
    expected_set = set(expected_ids)
    hits = len(top_k_set.intersection(expected_set))
    return hits / len(expected_set)


def precision_at_k(retrieved_ids: Sequence[str], expected_ids: Sequence[str], k: int) -> float:
    """Calculate Precision@K: fraction of top-K retrieved items that are relevant."""
    if k <= 0:
        return 0.0
    top_k_list = retrieved_ids[:k]
    if not top_k_list:
        return 0.0
    expected_set = set(expected_ids)
    hits = sum(1 for item in top_k_list if item in expected_set)
    return hits / min(k, len(top_k_list))


def reciprocal_rank(retrieved_ids: Sequence[str], expected_ids: Sequence[str]) -> float:
    """Calculate Reciprocal Rank (RR): 1 / rank of first relevant retrieved item."""
    expected_set = set(expected_ids)
    for idx, item in enumerate(retrieved_ids, start=1):
        if item in expected_set:
            return 1.0 / idx
    return 0.0


def ndcg_at_k(retrieved_ids: Sequence[str], expected_ids: Sequence[str], k: int) -> float:
    """Calculate nDCG@K with binary relevance."""
    if not expected_ids or k <= 0:
        return 1.0 if not expected_ids else 0.0

    expected_set = set(expected_ids)
    dcg = 0.0
    for idx, item in enumerate(retrieved_ids[:k], start=1):
        if item in expected_set:
            dcg += 1.0 / math.log2(idx + 1)

    # Ideal DCG (all relevant items at top)
    idcg = sum(1.0 / math.log2(idx + 1) for idx in range(1, min(len(expected_set), k) + 1))
    return dcg / idcg if idcg > 0 else 0.0


def calculate_retrieval_metrics(
    eval_runs: List[Dict[str, Any]]
) -> RetrievalMetricsResult:
    """
    Computes overall retrieval metrics over a batch of evaluation queries.
    Each run in eval_runs should contain:
      - 'retrieved_ids': List[str]
      - 'expected_ids': List[str]
      - 'latency_ms': float
    """
    if not eval_runs:
        return RetrievalMetricsResult()

    total_r1 = total_r5 = total_r10 = total_r20 = 0.0
    total_p1 = total_p5 = total_p10 = 0.0
    total_rr = total_ndcg5 = total_ndcg10 = 0.0
    latencies = []

    for run in eval_runs:
        retrieved = run.get("retrieved_ids", [])
        expected = run.get("expected_ids", [])
        lat = run.get("latency_ms", 0.0)

        total_r1 += recall_at_k(retrieved, expected, 1)
        total_r5 += recall_at_k(retrieved, expected, 5)
        total_r10 += recall_at_k(retrieved, expected, 10)
        total_r20 += recall_at_k(retrieved, expected, 20)

        total_p1 += precision_at_k(retrieved, expected, 1)
        total_p5 += precision_at_k(retrieved, expected, 5)
        total_p10 += precision_at_k(retrieved, expected, 10)

        total_rr += reciprocal_rank(retrieved, expected)
        total_ndcg5 += ndcg_at_k(retrieved, expected, 5)
        total_ndcg10 += ndcg_at_k(retrieved, expected, 10)

        latencies.append(lat)

    n = len(eval_runs)
    latencies.sort()

    p50_idx = int(0.50 * (n - 1))
    p95_idx = int(0.95 * (n - 1))
    p99_idx = int(0.99 * (n - 1))

    return RetrievalMetricsResult(
        recall_at_1=total_r1 / n,
        recall_at_5=total_r5 / n,
        recall_at_10=total_r10 / n,
        recall_at_20=total_r20 / n,
        precision_at_1=total_p1 / n,
        precision_at_5=total_p5 / n,
        precision_at_10=total_p10 / n,
        mrr=total_rr / n,
        ndcg_at_5=total_ndcg5 / n,
        ndcg_at_10=total_ndcg10 / n,
        latency_p50_ms=latencies[p50_idx] if latencies else 0.0,
        latency_p95_ms=latencies[p95_idx] if latencies else 0.0,
        latency_p99_ms=latencies[p99_idx] if latencies else 0.0,
        total_queries=n,
    )
