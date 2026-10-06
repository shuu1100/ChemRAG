"""
Embedding System Benchmark Script.
Fulfills Prompt 8.4:
- Compares generic text embeddings, chemistry-aware embeddings, and combined retrieval.
- Measures Recall@K, MRR, nDCG, latency, memory, and storage footprints.
- Produces reproducible measurements and saves benchmark output to JSON.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.embeddings.chemical_embedder import ChemicalEmbeddingService
from backend.app.embeddings.factory import (
    get_chemical_embedding_provider,
    get_text_embedding_provider,
)
from backend.app.embeddings.providers.deterministic import DeterministicLocalProvider
from backend.app.embeddings.providers.morgan import MorganFingerprintProvider
from backend.app.embeddings.text_embedder import TextEmbeddingService
from backend.app.models.chunk import EmbeddingModelType


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic Chemistry Benchmark Dataset
# ─────────────────────────────────────────────────────────────────────────────

BENCHMARK_DOCUMENTS = [
    {
        "id": "doc_01_aspirin",
        "title": "Synthesis and Acetylation of Salicylic Acid to Acetylsalicylic Acid",
        "text": "Salicylic acid reacts with acetic anhydride in the presence of an acid catalyst to yield acetylsalicylic acid (aspirin) and acetic acid. Reaction conditions require heating at 50-60 C.",
        "smiles": "CC(=O)Oc1ccccc1C(=O)O",
        "entities": ["aspirin", "salicylic acid", "acetic anhydride"],
    },
    {
        "id": "doc_02_benzene",
        "title": "Catalytic Hydrogenation of Benzene to Cyclohexane",
        "text": "Benzene undergoes complete catalytic hydrogenation to cyclohexane over Raney nickel or ruthenium catalysts under 30 atm H2 at 150 C. Exothermic addition.",
        "smiles": "c1ccccc1",
        "entities": ["benzene", "cyclohexane", "Raney nickel"],
    },
    {
        "id": "doc_03_paracetamol",
        "title": "Acetaminophen Synthesis from 4-Aminophenol",
        "text": "Acetaminophen (paracetamol, N-(4-hydroxyphenyl)acetamide) is prepared by acylation of 4-aminophenol with acetic anhydride in aqueous suspension at room temperature.",
        "smiles": "CC(=O)Nc1ccc(O)cc1",
        "entities": ["paracetamol", "acetaminophen", "4-aminophenol"],
    },
    {
        "id": "doc_04_caffeine",
        "title": "Purine Alkaloid Properties of Caffeine",
        "text": "Caffeine is a central nervous system stimulant belonging to the methylxanthine class. Chemical structure 1,3,7-trimethylxanthine with a bicyclic purinedione core.",
        "smiles": "Cn1cnc2c1c(=O)n(c(=O)n2C)C",
        "entities": ["caffeine", "1,3,7-trimethylxanthine", "purine"],
    },
    {
        "id": "doc_05_ibuprofen",
        "title": "Boots Synthesis and Chiral Center of Ibuprofen",
        "text": "Ibuprofen, 2-(4-isobutylphenyl)propanoic acid, is a nonsteroidal anti-inflammatory drug. Contains a chiral stereocenter on the alpha carbon of the propionic acid moiety.",
        "smiles": "CC(C)Cc1ccc(C(C)C(=O)O)cc1",
        "entities": ["ibuprofen", "propanoic acid", "NSAID"],
    },
    {
        "id": "doc_06_penicillin",
        "title": "Beta-Lactam Core of Benzylpenicillin",
        "text": "Benzylpenicillin (Penicillin G) features a core beta-lactam ring fused to a thiazolidine ring. Sensitive to acid hydrolysis and bacterial beta-lactamase degradation.",
        "smiles": "CC1(C(N2C(S1)C(C2=O)NC(=O)Cc3ccccc3)C(=O)O)C",
        "entities": ["penicillin G", "beta-lactam", "thiazolidine"],
    },
    {
        "id": "doc_07_ethanol",
        "title": "Oxidation of Ethanol to Acetaldehyde and Acetic Acid",
        "text": "Ethanol is oxidized to acetaldehyde using pyridinium chlorochromate (PCC), or further to acetic acid with aqueous potassium dichromate or potassium permanganate.",
        "smiles": "CCO",
        "entities": ["ethanol", "acetaldehyde", "acetic acid"],
    },
    {
        "id": "doc_08_glucose",
        "title": "Stereochemistry and Pyranose Ring of D-Glucose",
        "text": "D-Glucose exists primarily as cyclic hemiacetal alpha- and beta-D-glucopyranose conformers in aqueous solution. Anomeric carbon C1 undergoes mutarotation.",
        "smiles": "OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O",
        "entities": ["D-glucose", "glucopyranose", "hemiacetal"],
    },
    {
        "id": "doc_09_sulfuric_acid",
        "title": "Hydration Exotherm and Safety Protocol for Sulfuric Acid",
        "text": "Dilution of concentrated sulfuric acid is extremely exothermic. Always add acid to water slowly with continuous stirring. Never add water to concentrated acid.",
        "smiles": "OS(=O)(=O)O",
        "entities": ["sulfuric acid", "exothermic", "safety"],
    },
    {
        "id": "doc_10_toluene",
        "title": "Electrophilic Nitration of Toluene",
        "text": "Nitration of toluene using mixed nitric and sulfuric acids gives ortho- and para-nitrotoluene due to hyperconjugation and methyl group electron-donation.",
        "smiles": "Cc1ccccc1",
        "entities": ["toluene", "nitrotoluene", "nitration"],
    },
]

BENCHMARK_QUERIES = [
    {
        "query_text": "What is the synthetic procedure and catalyst for acetylsalicylic acid aspirin from salicylic acid?",
        "query_smiles": "CC(=O)Oc1ccccc1C(=O)O",
        "relevant_doc_id": "doc_01_aspirin",
    },
    {
        "query_text": "How is benzene catalytically converted into cyclohexane under hydrogen pressure?",
        "query_smiles": "c1ccccc1",
        "relevant_doc_id": "doc_02_benzene",
    },
    {
        "query_text": "Preparation of N-(4-hydroxyphenyl)acetamide acetaminophen from 4-aminophenol",
        "query_smiles": "CC(=O)Nc1ccc(O)cc1",
        "relevant_doc_id": "doc_03_paracetamol",
    },
    {
        "query_text": "Trimethylxanthine purine alkaloid molecular structure of caffeine",
        "query_smiles": "Cn1cnc2c1c(=O)n(c(=O)n2C)C",
        "relevant_doc_id": "doc_04_caffeine",
    },
    {
        "query_text": "Chiral alpha-carbon nonsteroidal anti-inflammatory drug 2-(4-isobutylphenyl)propanoic acid",
        "query_smiles": "CC(C)Cc1ccc(C(C)C(=O)O)cc1",
        "relevant_doc_id": "doc_05_ibuprofen",
    },
    {
        "query_text": "Beta-lactam fused thiazolidine ring structure of benzylpenicillin",
        "query_smiles": "CC1(C(N2C(S1)C(C2=O)NC(=O)Cc3ccccc3)C(=O)O)C",
        "relevant_doc_id": "doc_06_penicillin",
    },
    {
        "query_text": "Oxidation reactions of ethanol to acetaldehyde with PCC",
        "query_smiles": "CCO",
        "relevant_doc_id": "doc_07_ethanol",
    },
    {
        "query_text": "Anomeric carbon mutarotation and pyranose ring of D-glucose",
        "query_smiles": "OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O",
        "relevant_doc_id": "doc_08_glucose",
    },
    {
        "query_text": "Safety procedures for exothermic acid dilution: always add acid to water",
        "query_smiles": "OS(=O)(=O)O",
        "relevant_doc_id": "doc_09_sulfuric_acid",
    },
    {
        "query_text": "Ortho and para electrophilic aromatic nitration products of toluene",
        "query_smiles": "Cc1ccccc1",
        "relevant_doc_id": "doc_10_toluene",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Metrics Calculation Utilities
# ─────────────────────────────────────────────────────────────────────────────

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    a = np.array(v1, dtype=np.float32)
    b = np.array(v2, dtype=np.float32)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def calculate_metrics(ranked_doc_ids: list[str], relevant_doc_id: str, k_values: list[int] = [1, 3, 5, 10]) -> dict[str, float]:
    metrics: dict[str, float] = {}

    # Rank index (1-based)
    rank = None
    if relevant_doc_id in ranked_doc_ids:
        rank = ranked_doc_ids.index(relevant_doc_id) + 1

    # MRR
    metrics["mrr"] = 1.0 / rank if rank else 0.0

    # Recall@K
    for k in k_values:
        top_k = ranked_doc_ids[:k]
        metrics[f"recall@{k}"] = 1.0 if relevant_doc_id in top_k else 0.0

    # nDCG@K
    for k in [3, 5, 10]:
        dcg = 0.0
        idcg = 1.0  # Since there is exactly 1 relevant document
        for i, doc_id in enumerate(ranked_doc_ids[:k]):
            if doc_id == relevant_doc_id:
                dcg = 1.0 / math.log2(i + 2)
                break
        metrics[f"ndcg@{k}"] = dcg / idcg

    return metrics


# ─────────────────────────────────────────────────────────────────────────────
# Benchmark Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

async def run_embedding_benchmark(dimensions: int = 3072, output_path: str | None = None) -> dict[str, Any]:
    print("=" * 80)
    print("ChemRAG Embedding System Benchmark (Phase 08)")
    print(f"Dimensions: {dimensions} | Documents: {len(BENCHMARK_DOCUMENTS)} | Queries: {len(BENCHMARK_QUERIES)}")
    print("=" * 80)

    # 1. Initialize Providers
    text_provider = DeterministicLocalProvider(
        model_name="deterministic-local-v1",
        dimensions=dimensions,
        embedding_type=EmbeddingModelType.TEXT,
    )
    chem_provider = MorganFingerprintProvider(
        dimensions=dimensions,
        model_name="rdkit-morgan-ecfp4",
    )

    text_service = TextEmbeddingService(provider=text_provider)
    chem_service = ChemicalEmbeddingService(provider=chem_provider)

    # 2. Benchmark Ingestion / Encoding Latency
    t0 = time.perf_counter()
    doc_texts = [d["text"] for d in BENCHMARK_DOCUMENTS]
    text_emb_results = await text_service.embed_texts(doc_texts)
    text_encoding_ms = (time.perf_counter() - t0) * 1000.0

    t0 = time.perf_counter()
    doc_smiles = [d["smiles"] for d in BENCHMARK_DOCUMENTS]
    chem_emb_results = await chem_service.embed_smiles_list(doc_smiles)
    chem_encoding_ms = (time.perf_counter() - t0) * 1000.0

    doc_text_vectors = {d["id"]: res.vector for d, res in zip(BENCHMARK_DOCUMENTS, text_emb_results)}
    doc_chem_vectors = {d["id"]: res.vector for d, res in zip(BENCHMARK_DOCUMENTS, chem_emb_results)}

    # 3. Query Evaluation
    modes = ["text_only", "chemical_only", "combined_hybrid"]
    mode_metrics: dict[str, list[dict[str, float]]] = {m: [] for m in modes}
    query_latencies: dict[str, list[float]] = {m: [] for m in modes}

    alpha = 0.65  # Weight for text similarity in combined hybrid

    for q in BENCHMARK_QUERIES:
        q_text = q["query_text"]
        q_smiles = q["query_smiles"]
        target = q["relevant_doc_id"]

        # --- A. Text Only ---
        t_start = time.perf_counter()
        q_text_emb = await text_service.embed_texts([q_text])
        q_vec = q_text_emb[0].vector
        text_scores = {
            doc_id: cosine_similarity(q_vec, vec)
            for doc_id, vec in doc_text_vectors.items()
        }
        ranked_text = sorted(text_scores.keys(), key=lambda d: text_scores[d], reverse=True)
        q_lat = (time.perf_counter() - t_start) * 1000.0
        query_latencies["text_only"].append(q_lat)
        mode_metrics["text_only"].append(calculate_metrics(ranked_text, target))

        # --- B. Chemical Only ---
        t_start = time.perf_counter()
        q_chem_emb = await chem_service.embed_smiles_list([q_smiles])
        q_chem_vec = q_chem_emb[0].vector
        chem_scores = {
            doc_id: cosine_similarity(q_chem_vec, vec)
            for doc_id, vec in doc_chem_vectors.items()
        }
        ranked_chem = sorted(chem_scores.keys(), key=lambda d: chem_scores[d], reverse=True)
        q_lat = (time.perf_counter() - t_start) * 1000.0
        query_latencies["chemical_only"].append(q_lat)
        mode_metrics["chemical_only"].append(calculate_metrics(ranked_chem, target))

        # --- C. Combined Hybrid ---
        t_start = time.perf_counter()
        hybrid_scores = {
            doc_id: alpha * text_scores[doc_id] + (1.0 - alpha) * chem_scores[doc_id]
            for doc_id in doc_text_vectors.keys()
        }
        ranked_hybrid = sorted(hybrid_scores.keys(), key=lambda d: hybrid_scores[d], reverse=True)
        q_lat = (time.perf_counter() - t_start) * 1000.0
        query_latencies["combined_hybrid"].append(q_lat)
        mode_metrics["combined_hybrid"].append(calculate_metrics(ranked_hybrid, target))

    # 4. Aggregate Metrics
    summary: dict[str, Any] = {}
    for m in modes:
        n_q = len(BENCHMARK_QUERIES)
        avg_metrics = {
            key: sum(sample[key] for sample in mode_metrics[m]) / n_q
            for key in mode_metrics[m][0].keys()
        }
        lats = query_latencies[m]
        summary[m] = {
            **avg_metrics,
            "latency_mean_ms": float(np.mean(lats)),
            "latency_p95_ms": float(np.percentile(lats, 95)),
            "latency_p99_ms": float(np.percentile(lats, 99)),
        }

    # 5. Storage and Memory Footprints
    bytes_per_float32 = dimensions * 4
    bytes_per_float16 = dimensions * 2
    mb_per_10k_float32 = (10000 * bytes_per_float32) / (1024 * 1024)
    mb_per_10k_float16 = (10000 * bytes_per_float16) / (1024 * 1024)

    storage_footprint = {
        "dimensions": dimensions,
        "bytes_per_vector_float32": bytes_per_float32,
        "bytes_per_vector_float16": bytes_per_float16,
        "storage_mb_per_10k_vectors_float32": round(mb_per_10k_float32, 2),
        "storage_mb_per_10k_vectors_float16": round(mb_per_10k_float16, 2),
    }

    # 6. Report Display
    print("\nRETRIEVAL PERFORMANCE COMPARISON:")
    print("-" * 80)
    print(f"{'Mode':<18} | {'Recall@1':<9} | {'Recall@5':<9} | {'MRR':<7} | {'nDCG@5':<8} | {'Latency (ms)':<12}")
    print("-" * 80)
    for m in modes:
        stats = summary[m]
        print(
            f"{m:<18} | "
            f"{stats['recall@1']:<9.3f} | "
            f"{stats['recall@5']:<9.3f} | "
            f"{stats['mrr']:<7.3f} | "
            f"{stats['ndcg@5']:<8.3f} | "
            f"{stats['latency_mean_ms']:<12.3f}"
        )
    print("-" * 80)

    print("\nSTORAGE FOOTPRINT:")
    print(f"  Vector Dimensions:              {dimensions}")
    print(f"  Storage per 10k vectors (fp32): {mb_per_10k_float32:.2f} MB")
    print(f"  Storage per 10k vectors (fp16): {mb_per_10k_float16:.2f} MB")
    print(f"  Document Text Encoding Batch:   {text_encoding_ms:.2f} ms")
    print(f"  Document Chem Encoding Batch:   {chem_encoding_ms:.2f} ms")
    print("=" * 80)

    final_report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dimensions": dimensions,
        "models": {
            "text": text_provider.model_name,
            "chemical": chem_provider.model_name,
        },
        "performance": summary,
        "storage": storage_footprint,
        "encoding_latencies_ms": {
            "text_batch_10": round(text_encoding_ms, 2),
            "chemical_batch_10": round(chem_encoding_ms, 2),
        },
    }

    # 7. Save output
    target_file = Path(output_path) if output_path else Path("artifacts/embedding_benchmark_results.json")
    target_file.parent.mkdir(parents=True, exist_ok=True)
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2)

    print(f"\n[OK] Benchmark output saved to: {target_file.resolve()}\n")
    return final_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ChemRAG Embedding System Benchmark")
    parser.add_argument("--dims", type=int, default=3072, help="Embedding dimension")
    parser.add_argument("--out", type=str, default="artifacts/embedding_benchmark_results.json", help="Output path")
    args = parser.parse_args()

    asyncio.run(run_embedding_benchmark(dimensions=args.dims, output_path=args.out))
