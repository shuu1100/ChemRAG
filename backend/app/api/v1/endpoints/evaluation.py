"""
ChemRAG — Evaluation REST API Endpoints
=======================================
Endpoints:
- POST /evaluation/run   (Run full RAGAS, retrieval, and chemistry evaluation suite)
- GET  /evaluation/runs  (Fetch historical evaluation runs)
"""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, status
from pydantic import BaseModel

from backend.app.evaluation.runner import EvaluationRunner

router = APIRouter()
eval_runner = EvaluationRunner()

# Persistent in-memory evaluation runs history
_evaluation_history: List[Dict[str, Any]] = []


class EvaluationRunRequest(BaseModel):
    target_recall_5: float = 0.80
    target_faithfulness: float = 0.85
    target_chemistry_valency: float = 0.90


@router.post(
    "/run",
    status_code=status.HTTP_200_OK,
    summary="Run full evaluation and regression suite",
)
async def run_evaluation(payload: EvaluationRunRequest = EvaluationRunRequest()) -> Dict[str, Any]:
    """Execute complete benchmark suite across retrieval, RAGAS, and chemistry reasoning."""
    report = await eval_runner.run_suite(
        target_recall_5=payload.target_recall_5,
        target_faithfulness=payload.target_faithfulness,
        target_chemistry_valency=payload.target_chemistry_valency,
    )
    data = report.to_dict()
    _evaluation_history.append(data)
    return data


@router.get(
    "/runs",
    status_code=status.HTTP_200_OK,
    summary="Get historical evaluation run reports",
)
async def get_evaluation_runs() -> List[Dict[str, Any]]:
    """Fetch past evaluation runs."""
    return _evaluation_history
