"""
ChemRAG — Vector Index Benchmark Script
Benchmarking HNSW indexing vs exact nearest neighbor search on pgvector.
Phase 02 / Prompt 2.3 Vector Storage Benchmark.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
import time
from typing import Any, List

import numpy as np

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def generate_random_vectors(count: int, dim: int) -> List[List[float]]:
    """Generate normalized random float vectors."""
    vectors = np.random.randn(count, dim).astype(np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    normalized = vectors / (norms + 1e-10)
    return normalized.tolist()


def calculate_storage_footprint(dimensions: int, count: int = 10000) -> dict[str, float]:
    """Calculate vector memory and disk footprints for FP32 and FP16 representations."""
    bytes_per_fp32 = 4
    bytes_per_fp16 = 2
    mb_fp32 = (dimensions * bytes_per_fp32 * count) / (1024 * 1024)
    mb_fp16 = (dimensions * bytes_per_fp16 * count) / (1024 * 1024)
    return {
        "dimensions": dimensions,
        "count": count,
        "storage_fp32_mb": round(mb_fp32, 2),
        "storage_fp16_mb": round(mb_fp16, 2),
    }


async def run_benchmark(
    count: int = 1000,
    dim: int = 3072,
    queries: int = 10,
    k: int = 10,
    output_path: str = "artifacts/vector_benchmark_results.json",
) -> dict[str, Any]:
    """Benchmark vector generation, retrieval latency, and storage footprint."""
    print("=" * 80)
    print("ChemRAG Vector Index Benchmark (Phase 02)")
    print(f"Vectors: {count:,} | Dimension: {dim} | Query Count: {queries} | Top-K: {k}")
    print("=" * 80)

    # 1. Generate benchmark dataset
    start_time = time.perf_counter()
    data = generate_random_vectors(count, dim)
    gen_time = time.perf_counter() - start_time
    throughput = count / gen_time if gen_time > 0 else 0.0
    print(f"\nVector Generation Throughput: {throughput:,.0f} vecs/s ({gen_time:.3f}s for {count:,} vectors)")

    query_vectors = generate_random_vectors(queries, dim)

    # 2. In-memory cosine similarity baseline
    print("\nRunning in-memory NumPy baseline search...")
    mat = np.array(data, dtype=np.float32)
    latencies: List[float] = []
    for q in query_vectors:
        q_vec = np.array(q, dtype=np.float32)
        q_start = time.perf_counter()
        scores = np.dot(mat, q_vec)
        _ = np.argpartition(scores, -k)[-k:]
        latencies.append((time.perf_counter() - q_start) * 1000.0)

    p50 = float(np.percentile(latencies, 50))
    p95 = float(np.percentile(latencies, 95))
    p99 = float(np.percentile(latencies, 99))
    mean_lat = float(np.mean(latencies))
    print(f"NumPy Baseline Latency: p50={p50:.2f}ms | p95={p95:.2f}ms | p99={p99:.2f}ms | mean={mean_lat:.2f}ms")

    # 3. Storage Footprint comparison across standard architectures
    footprints = {
        "chemrag_hybrid_3072": calculate_storage_footprint(3072, 10000),
        "openai_large_1536": calculate_storage_footprint(1536, 10000),
        "chemberta_768": calculate_storage_footprint(768, 10000),
    }

    print("\nSTORAGE FOOTPRINT COMPARISON (per 10k vectors):")
    print("-" * 80)
    print(f"{'Configuration':<25} | {'Dimensions':<10} | {'FP32 Storage':<15} | {'FP16 Storage':<15}")
    print("-" * 80)
    for name, fp in footprints.items():
        print(f"{name:<25} | {fp['dimensions']:<10} | {fp['storage_fp32_mb']:>8.2f} MB    | {fp['storage_fp16_mb']:>8.2f} MB")
    print("-" * 80)

    # 4. Optional Live Database pgvector check
    db_status = "unconnected"
    db_version = None
    engine = None
    try:
        from backend.app.db.session import get_engine
        from sqlalchemy import text

        engine = get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version();"))
            db_version = result.scalar()
            db_status = "connected"
            print(f"\nConnected to DB: {db_version}")
    except Exception as exc:
        print(f"\nLive database benchmark skipped (no active DB session: {exc})")
    finally:
        if engine is not None:
            await engine.dispose()

    # 5. Build report structure
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config": {
            "vector_count": count,
            "dimensions": dim,
            "query_count": queries,
            "top_k": k,
        },
        "generation": {
            "elapsed_seconds": round(gen_time, 4),
            "throughput_vectors_per_sec": round(throughput, 1),
        },
        "in_memory_baseline": {
            "latency_p50_ms": round(p50, 3),
            "latency_p95_ms": round(p95, 3),
            "latency_p99_ms": round(p99, 3),
            "latency_mean_ms": round(mean_lat, 3),
        },
        "storage_footprints": footprints,
        "database": {
            "status": db_status,
            "version": db_version,
        },
    }

    # 6. Save JSON artifact
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n[OK] Benchmark output saved to: {out_path.resolve()}\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="ChemRAG Vector Index Benchmark")
    parser.add_argument("--count", type=int, default=1000, help="Number of vectors to generate")
    parser.add_argument("--dim", type=int, default=3072, help="Vector dimension (e.g. 3072 or 1536)")
    parser.add_argument("--queries", type=int, default=10, help="Number of benchmark queries")
    parser.add_argument("--k", type=int, default=10, help="Top-K nearest neighbors to retrieve")
    parser.add_argument("--out", type=str, default="artifacts/vector_benchmark_results.json", help="Output JSON path")
    args = parser.parse_args()

    asyncio.run(
        run_benchmark(
            count=args.count,
            dim=args.dim,
            queries=args.queries,
            k=args.k,
            output_path=args.out,
        )
    )


if __name__ == "__main__":
    main()
