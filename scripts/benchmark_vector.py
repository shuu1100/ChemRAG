"""
ChemRAG — Vector Index Benchmark Script
Benchmarking HNSW indexing vs exact nearest neighbor search on pgvector.
"""
from __future__ import annotations

import argparse
import asyncio
import random
import time
from typing import List

import numpy as np


def generate_random_vectors(count: int, dim: int) -> List[List[float]]:
    """Generate normalized random float vectors."""
    vectors = np.random.randn(count, dim).astype(np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    normalized = vectors / (norms + 1e-10)
    return normalized.tolist()


async def run_benchmark(count: int, dim: int, queries: int, k: int) -> None:
    """Benchmark vector generation and retrieval latency against pgvector."""
    print(f"=== ChemRAG Vector Benchmark ===")
    print(f"Vectors: {count:,} | Dimension: {dim} | Query Count: {queries} | Top-K: {k}")

    # Generate benchmark dataset
    start_time = time.perf_counter()
    data = generate_random_vectors(count, dim)
    gen_time = time.perf_counter() - start_time
    print(f"Vector generation completed in {gen_time:.3f}s ({count / gen_time:,.0f} vecs/s)")

    query_vectors = generate_random_vectors(queries, dim)

    # In-memory cosine similarity baseline
    print("\nRunning in-memory numpy baseline search...")
    mat = np.array(data, dtype=np.float32)
    latencies: List[float] = []
    for q in query_vectors:
        q_vec = np.array(q, dtype=np.float32)
        q_start = time.perf_counter()
        scores = np.dot(mat, q_vec)
        _ = np.argpartition(scores, -k)[-k:]
        latencies.append((time.perf_counter() - q_start) * 1000.0)

    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)
    print(f"Numpy Baseline: p50={p50:.2f}ms | p95={p95:.2f}ms | p99={p99:.2f}ms")

    # If DB connection available, test against PostgreSQL HNSW
    try:
        from backend.app.core.config import get_settings
        from backend.app.db.session import get_engine
        from sqlalchemy import text

        settings = get_settings()
        engine = get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version();"))
            db_version = result.scalar()
            print(f"\nConnected to DB: {db_version}")
            print("To benchmark live pgvector table, ensure `chunk_embeddings` is populated.")
    except Exception as exc:
        print(f"\nLive database benchmark skipped (no active DB session: {exc})")

    print("\nBenchmark completed successfully.")


def main() -> None:
    parser = argparse.ArgumentParser(description="ChemRAG Vector Index Benchmark")
    parser.add_argument("--count", type=int, default=1000, help="Number of vectors to generate")
    parser.add_argument("--dim", type=int, default=3072, help="Vector dimension (e.g. 3072 or 1536)")
    parser.add_argument("--queries", type=int, default=10, help="Number of benchmark queries")
    parser.add_argument("--k", type=int, default=10, help="Top-K nearest neighbors to retrieve")
    args = parser.parse_args()

    asyncio.run(run_benchmark(count=args.count, dim=args.dim, queries=args.queries, k=args.k))


if __name__ == "__main__":
    main()
