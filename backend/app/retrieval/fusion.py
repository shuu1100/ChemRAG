"""
Reciprocal Rank Fusion (RRF).
Fulfills Prompt 9.4:
- Fuses semantic, lexical, and optional chemical results using:
  RRF_score = Σ (w_m / (k + rank_i))
  Default k = 60 (configurable).
- Stores component ranks and scores in score_breakdown.
- Returns deterministic, reproducible ranked outputs.
"""

from __future__ import annotations

import logging
from typing import Any, Sequence
import uuid

from backend.app.retrieval.models import ScoredChunk

logger = logging.getLogger(__name__)


class ReciprocalRankFusion:
    """
    Fuses multiple ranked retrieval candidate lists into a single consolidated ranking.
    Deterministic tie-breaking ensures reproducibility across runs.
    """

    def __init__(
        self,
        k: int = 60,
        weights: dict[str, float] | None = None,
    ) -> None:
        self.k = k
        self.weights = weights or {
            "semantic": 1.0,
            "lexical": 1.0,
            "chemical": 1.0,
        }

    def fuse(
        self,
        retrieval_results: dict[str, list[ScoredChunk]],
        top_k: int = 10,
    ) -> list[ScoredChunk]:
        """
        Merge ranked lists from multiple retrieval modalities using weighted RRF.
        """
        rrf_scores: dict[uuid.UUID, float] = {}
        chunk_map: dict[uuid.UUID, ScoredChunk] = {}
        component_ranks: dict[uuid.UUID, dict[str, int]] = {}
        component_scores: dict[uuid.UUID, dict[str, float]] = {}

        # 1. Accumulate RRF scores and record ranks
        for modality, chunks in retrieval_results.items():
            weight = self.weights.get(modality, 1.0)
            for rank_0, chunk in enumerate(chunks):
                rank = rank_0 + 1  # 1-based rank
                cid = chunk.chunk_id

                if cid not in chunk_map:
                    chunk_map[cid] = chunk
                    component_ranks[cid] = {}
                    component_scores[cid] = {}
                    rrf_scores[cid] = 0.0

                # Weighted RRF score contribution
                contribution = weight / (self.k + rank)
                rrf_scores[cid] += contribution

                component_ranks[cid][f"{modality}_rank"] = rank
                component_scores[cid][f"{modality}_score"] = chunk.score

        if not chunk_map:
            return []

        # 2. Deterministic sorting:
        # Primary: descending RRF score
        # Secondary: maximum component score
        # Tertiary: chunk_id string (guarantees 100% deterministic ordering)
        def sort_key(cid: uuid.UUID) -> tuple[float, float, str]:
            max_comp = max(component_scores[cid].values()) if component_scores[cid] else 0.0
            return (-rrf_scores[cid], -max_comp, str(cid))

        sorted_cids = sorted(chunk_map.keys(), key=sort_key)

        # 3. Build fused ScoredChunk instances
        final_results: list[ScoredChunk] = []
        for new_rank, cid in enumerate(sorted_cids[:top_k], start=1):
            original = chunk_map[cid]

            combined_breakdown: dict[str, Any] = {
                "rrf_score": rrf_scores[cid],
                "rrf_k": self.k,
                **component_ranks[cid],
                **component_scores[cid],
            }
            # Carry over highlights or match_type if present
            if "highlight" in original.score_breakdown:
                combined_breakdown["highlight"] = original.score_breakdown["highlight"]
            if "match_type" in original.score_breakdown:
                combined_breakdown["match_type"] = original.score_breakdown["match_type"]

            fused_chunk = ScoredChunk(
                chunk_id=original.chunk_id,
                document_id=original.document_id,
                document_title=original.document_title,
                content=original.content,
                raw_text=original.raw_text,
                retrieval_text=original.retrieval_text,
                display_text=original.display_text,
                chunk_type=original.chunk_type,
                chunk_index=original.chunk_index,
                page_number=original.page_number,
                bbox=original.bbox,
                score=rrf_scores[cid],
                rank=new_rank,
                retrieval_mode="hybrid_rrf",
                score_breakdown=combined_breakdown,
                metadata=original.metadata,
            )
            final_results.append(fused_chunk)

        return final_results
