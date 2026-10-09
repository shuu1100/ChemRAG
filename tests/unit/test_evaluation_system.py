"""
ChemRAG — Phase 17 Unit Tests: Evaluation & Regression Suite
=============================================================
Tests:
- Retrieval dataset loading & benchmark schemas
- Quantitative retrieval metrics (Recall@K, MRR, nDCG@K, Precision@K)
- RAGAS-style metrics (Context Precision/Recall, Faithfulness, Relevance)
- Chemistry domain evaluation (SMILES valency, formulas, units)
- EvaluationRunner regression suite execution
"""
from __future__ import annotations

import pytest

from backend.app.evaluation.chemistry_eval import ChemistryEvaluator
from backend.app.evaluation.dataset import get_default_benchmark_dataset
from backend.app.evaluation.metrics import (
    calculate_retrieval_metrics,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from backend.app.evaluation.ragas_eval import RagasEvaluator
from backend.app.evaluation.runner import EvaluationRunner


def test_benchmark_dataset_loading():
    """Verify default benchmark dataset items."""
    dataset = get_default_benchmark_dataset()
    assert len(dataset) >= 5
    first = dataset[0]
    assert first.id == "chem-eval-001"
    assert first.query_smiles == "CCO"


def test_retrieval_metrics_calculations():
    """Verify Recall@K, Precision@K, MRR, and nDCG math."""
    retrieved = ["c-1", "c-2", "c-3", "c-4", "c-5"]
    expected = ["c-2", "c-4"]

    assert recall_at_k(retrieved, expected, 5) == 1.0  # both in top 5
    assert recall_at_k(retrieved, expected, 1) == 0.0  # c-1 not expected
    assert precision_at_k(retrieved, expected, 5) == 2 / 5
    assert reciprocal_rank(retrieved, expected) == 0.5  # first hit at rank 2 (c-2)
    assert ndcg_at_k(retrieved, expected, 5) > 0.0


def test_ragas_evaluator_metrics():
    """Verify RAGAS context precision, recall, faithfulness, and relevance."""
    evaluator = RagasEvaluator()

    query = "What is the boiling point of Ethanol?"
    context = ["Ethanol (C2H6O) has a boiling point of 78.37 °C at 1 atm."]
    answer = "Ethanol has a boiling point of 78.37 °C."

    res = evaluator.evaluate_item(
        query=query,
        retrieved_contexts=context,
        generated_answer=answer,
        expected_answer=answer,
    )

    assert res.context_precision == 1.0
    assert res.faithfulness == 1.0
    assert res.answer_relevance >= 0.75
    assert res.overall_ragas_score >= 0.85


def test_chemistry_evaluator_valency():
    """Verify RDKit SMILES valency and formula evaluation."""
    chem_eval = ChemistryEvaluator()

    cases = [
        {"id": "t-1", "smiles": "CCO", "formula": "C2H6O", "text": "Boiling point is 78.37 °C"},
        {"id": "t-2", "smiles": "c1ccccc1", "formula": "C6H6", "text": "Benzene ring structure"},
    ]

    res = chem_eval.evaluate_chemistry_answers(cases)
    assert res.smiles_valency_score == 1.0
    assert res.formula_accuracy_score == 1.0
    assert res.overall_chemistry_score == 1.0


@pytest.mark.asyncio
async def test_evaluation_runner():
    """Verify EvaluationRunner executes full benchmark suite."""
    runner = EvaluationRunner()
    report = await runner.run_suite()

    assert report.run_id.startswith("eval-")
    assert report.retrieval_metrics["recall_at_5"] == 1.0
    assert report.ragas_metrics["overall_ragas_score"] > 0.0
    assert report.chemistry_metrics["overall_chemistry_score"] >= 0.90
    assert report.overall_passed is True
