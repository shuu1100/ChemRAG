"""
Chemical Embedding Service.
Fulfills Prompt 8.3:
- For chunks containing molecular structures or chemical entities,
  canonicalizes structures using RDKit.
- Generates molecular embeddings using chemistry-compatible models (ChemBERTa / Morgan / MoLFormer).
- Stores chemical vectors separately from text vectors (embedding_type = CHEMICAL).
"""

from __future__ import annotations

import logging
from typing import Any, Sequence
import uuid

from rdkit import Chem

from backend.app.chunking.models import ChunkPayload
from backend.app.embeddings.base import (
    BaseEmbeddingProvider,
    EmbeddingDimensionMismatchError,
    EmbeddingError,
    EmbeddingResult,
)
from backend.app.embeddings.factory import get_chemical_embedding_provider
from backend.app.models.chunk import Chunk, ChunkEmbedding, EmbeddingModelType

logger = logging.getLogger(__name__)


class ChemicalEmbeddingService:
    """
    Orchestrates chemical structure canonicalization and molecular embedding generation.
    Stores and tags chemical vectors separately from general text vectors.
    """

    def __init__(
        self,
        provider: BaseEmbeddingProvider | None = None,
        batch_size: int = 100,
    ) -> None:
        self.provider = provider or get_chemical_embedding_provider()
        self.batch_size = batch_size

    def canonicalize_smiles(self, raw_smiles: str) -> str | None:
        """
        Validate and canonicalize a chemical SMILES string using RDKit.
        Returns canonical SMILES if valid, otherwise None.
        """
        if not raw_smiles or not raw_smiles.strip():
            return None
        try:
            mol = Chem.MolFromSmiles(raw_smiles.strip())
            if mol is not None:
                return Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)
        except Exception as exc:
            logger.debug("Failed to parse SMILES '%s': %s", raw_smiles, exc)
        return None

    def extract_chemical_representations(
        self,
        chunk: ChunkPayload | Chunk,
    ) -> list[str]:
        """
        Extract candidate molecular structures (SMILES) or chemical entities from a chunk.
        """
        candidates: list[str] = []

        if isinstance(chunk, ChunkPayload):
            for entity in chunk.chemical_entities:
                # Check entity attributes or dict keys
                if isinstance(entity, dict):
                    smiles = entity.get("smiles") or entity.get("canonical_smiles")
                    if smiles:
                        candidates.append(smiles)
                    elif entity.get("text"):
                        candidates.append(entity["text"])
                elif hasattr(entity, "smiles") and entity.smiles:
                    candidates.append(entity.smiles)
                elif hasattr(entity, "text") and entity.text:
                    candidates.append(entity.text)

            # If no entities explicitly listed, check metadata or inspect text for SMILES
            if not candidates and chunk.metadata.get("smiles"):
                candidates.append(chunk.metadata["smiles"])

        elif isinstance(chunk, Chunk):
            # Check attached chemical entities relationship if present
            if hasattr(chunk, "chemical_entities") and chunk.chemical_entities:
                for ce in chunk.chemical_entities:
                    if hasattr(ce, "entity") and ce.entity and ce.entity.smiles:
                        candidates.append(ce.entity.smiles)

        return candidates

    async def embed_smiles_list(self, smiles_list: Sequence[str]) -> list[EmbeddingResult]:
        """
        Canonicalize a sequence of SMILES strings and generate chemical vector embeddings.
        """
        if not smiles_list:
            return []

        canonicalized: list[str] = []
        for s in smiles_list:
            can = self.canonicalize_smiles(s)
            canonicalized.append(can if can else s)

        batch_res = await self.provider.embed_batch(canonicalized)
        if batch_res.failed_indices:
            logger.warning(
                "Chemical embedding had %d failed items out of %d.",
                len(batch_res.failed_indices),
                len(canonicalized),
            )

        # Validate dimensions
        for res in batch_res.results:
            if res.dimensions != self.provider.dimensions:
                raise EmbeddingDimensionMismatchError(
                    expected=self.provider.dimensions,
                    received=res.dimensions,
                    model_name=self.provider.model_name,
                )

        return batch_res.results

    async def embed_chunks_with_chemistry(
        self,
        chunks: Sequence[ChunkPayload | Chunk],
    ) -> list[tuple[uuid.UUID | None, EmbeddingResult]]:
        """
        Identify chunks with molecular structures, canonicalize them,
        generate chemical embeddings, and return (chunk_id, EmbeddingResult) pairs.
        Chunks lacking chemical structures are cleanly omitted.
        """
        paired_candidates: list[tuple[uuid.UUID | None, str]] = []

        for c in chunks:
            reps = self.extract_chemical_representations(c)
            chunk_id = c.chunk_id if isinstance(c, ChunkPayload) else getattr(c, "id", None)
            for rep in reps:
                paired_candidates.append((chunk_id, rep))

        if not paired_candidates:
            return []

        smiles_to_embed = [pair[1] for pair in paired_candidates]
        results = await self.embed_smiles_list(smiles_to_embed)

        output: list[tuple[uuid.UUID | None, EmbeddingResult]] = []
        for (chunk_id, _), emb_res in zip(paired_candidates, results):
            output.append((chunk_id, emb_res))

        return output

    def create_chemical_chunk_embedding_model(
        self,
        chunk_id: uuid.UUID,
        embedding_result: EmbeddingResult,
        is_half_precision: bool = False,
    ) -> ChunkEmbedding:
        """
        Create a ChunkEmbedding SQLAlchemy database model tagged with
        EmbeddingModelType.CHEMICAL, ensuring chemical vectors remain
        strictly separated from text vectors in storage and indexing.
        """
        meta = embedding_result.metadata
        return ChunkEmbedding(
            chunk_id=chunk_id,
            embedding_type=EmbeddingModelType.CHEMICAL,
            model_name=meta.model_name,
            model_version=meta.model_version,
            dimensions=embedding_result.dimensions,
            embedding=embedding_result.vector,
            is_half_precision=is_half_precision,
            norm=embedding_result.norm,
        )
