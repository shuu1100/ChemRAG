"""
ChemRAG — Automated Regression Suite Script
============================================
Runs evaluation benchmarks for retrieval, RAGAS, chemistry domain reasoning,
and safety to detect regressions automatically.

Usage:
    python scripts/run_regression_suite.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.evaluation.runner import EvaluationRunner


async def main() -> int:
    print("==================================================================")
    print("ChemRAG — System Evaluation & Regression Benchmark Suite")
    print("==================================================================")

    runner = EvaluationRunner()
    report = await runner.run_suite()

    print(f"\n[+] Run ID: {report.run_id}")
    print(f"[+] Duration: {report.duration_ms:.2f} ms")
    print("\n--- Retrieval Metrics ---")
    for k, v in report.retrieval_metrics.items():
        print(f"  - {k}: {v}")

    print("\n--- RAGAS Generation Metrics ---")
    for k, v in report.ragas_metrics.items():
        print(f"  - {k}: {v}")

    print("\n--- Chemistry Domain Validation ---")
    for k, v in report.chemistry_metrics.items():
        print(f"  - {k}: {v}")

    if report.regression_warnings:
        print("\n[!] REGRESSION WARNINGS DETECTED:")
        for w in report.regression_warnings:
            print(f"  - {w}")

    print(f"\nOverall Result: {'PASSED' if report.overall_passed else 'FAILED'}")
    return 0 if report.overall_passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
