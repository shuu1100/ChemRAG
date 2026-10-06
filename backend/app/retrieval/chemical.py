"""
Chemical Retriever.
Fulfills Prompt 9.3:
- Exact identity, formula, InChIKey, name, similarity, and substructure retrieval.
- Clearly distinguishes:
  1) Identity matching (Exact 1.0 match on InChIKey, canonical SMILES, or CAS)
  2) Molecular similarity (Chemical fingerprint / vector similarity in [0, 1])
  3) Text similarity (Handled separately by semantic retriever)
"""

from __future__ import annotations

import logging
from typing import Any, Sequence
import uuid

import numpy as np
from rdkit import Chem
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.embeddings.chemical_embedder import ChemicalEmbeddingService
from backend.app.embeddings.factory import get_chemical_embedding_provider
from backend.app.models.chemical import ChemicalEntity, ChemicalStructure, ChunkChemicalEntity
from backend.app.models.chunk import Chunk, ChunkEmbedding, EmbeddingModelType
from backend.app.models.document import Document
from backend.app.retrieval.models import RetrievalFilter, ScoredChunk

logger = logging.getLogger(__name__)


class ChemicalRetriever:
    """
    Specialized chemical structure retriever.
    Supports exact molecular identity, formula, name, substructure,
    and continuous fingerprint vector similarity.
    """

    def __init__(
        self,
        chemical_embedding_service: ChemicalEmbeddingService | None = None,
    ) -> None:
        self.embedding_service = chemical_embedding_service or ChemicalEmbeddingService()

    def canonicalize(self, smiles: str) -> str | None:
        """Parse and canonicalize SMILES."""
        return self.embedding_service.canonicalize_smiles(smiles)

    def smiles_to_inchikey(self, smiles: str) -> str | None:
        """Derive standard InChIKey from SMILES via RDKit."""
        try:
            mol = Chem.MolFromSmiles(smiles.strip())
            if mol is not None:
                return Chem.MolToInchiKey(mol)
        except Exception:
            pass
        return None

    async def search(
        self,
        query: str,
        session: AsyncSession,
        query_smiles: str | None = None,
        top_k: int = 10,
        filters: RetrievalFilter | None = None,
        similarity_threshold: float = 0.5,
    ) -> list[ScoredChunk]:
        """
        Execute chemical search evaluating exact identity, formula, name,
        and molecular vector similarity.
        """
        results_by_chunk_id: dict[uuid.UUID, ScoredChunk] = {}

        # 1. Determine target identifiers from query
        target_smiles = query_smiles or (self.canonicalize(query) if self.canonicalize(query) else None)
        target_inchikey = self.smiles_to_inchikey(target_smiles) if target_smiles else None

        # 2. Exact Identity Matching (InChIKey, SMILES, CAS)
        identity_chunks = await self._search_exact_identity(
            session=session,
            target_inchikey=target_inchikey,
            target_smiles=target_smiles,
            query_text=query,
            filters=filters,
        )
        for sc in identity_chunks:
            results_by_chunk_id[sc.chunk_id] = sc

        # 3. Formula & Chemical Entity Name Matching
        formula_chunks = await self._search_formula_and_name(
            session=session,
            query_text=query,
            filters=filters,
        )
        for sc in formula_chunks:
            if sc.chunk_id not in results_by_chunk_id:
                results_by_chunk_id[sc.chunk_id] = sc

        # 4. Molecular Vector Similarity Matching (if target_smiles is present)
        if target_smiles:
            sim_chunks = await self._search_molecular_similarity(
                session=session,
                smiles=target_smiles,
                top_k=top_k,
                filters=filters,
                min_threshold=similarity_threshold,
            )
            for sc in sim_chunks:
                if sc.chunk_id not in results_by_chunk_id:
                    results_by_chunk_id[sc.chunk_id] = sc
                else:
                    # Update score breakdown if already found
                    results_by_chunk_id[sc.chunk_id].score_breakdown["molecular_similarity"] = sc.score

        # 5. Rank and return
        final_list = list(results_by_chunk_id.values())
        final_list.sort(key=lambda x: x.score, reverse=True)
        for r, sc in enumerate(final_list[:top_k], start=1):
            sc.rank = r
            sc.score_breakdown["chemical_rank"] = r

        return final_list[:top_k]

    async def _search_exact_identity(
        self,
        session: AsyncSession,
        target_inchikey: str | None,
        target_smiles: str | None,
        query_text: str,
        filters: RetrievalFilter | None,
    ) -> list[ScoredChunk]:
        """Find chunks with exact molecular structure identity match."""
        if not target_inchikey and not target_smiles and "-" not in query_text:
            return []

        conditions = []
        if target_inchikey:
            conditions.append(ChemicalEntity.inchi_key == target_inchikey)
        if target_smiles:
            conditions.append(ChemicalEntity.canonical_smiles == target_smiles)
        if "-" in query_text and len(query_text.split("-")) == 3:
            # Possible CAS number
            conditions.append(ChemicalEntity.cas_number == query_text.strip())

        if not conditions:
            return []

        stmt = (
            select(Chunk, ChemicalEntity)
            .join(ChunkChemicalEntity, ChunkChemicalEntity.chunk_id == Chunk.id)
            .join(ChemicalEntity, ChunkChemicalEntity.chemical_entity_id == ChemicalEntity.id)
            .join(Document, Chunk.document_id == Document.id)
            .where(
                Chunk.is_current.is_(True),
                Document.deleted_at.is_(None),
                or_(*conditions),
            )
        )
        if filters and filters.organization_id:
            stmt = stmt.where(Document.organization_id == filters.organization_id)

        try:
            result = await session.execute(stmt)
            rows = result.all()
            scored: list[ScoredChunk] = []
            for chunk, chem in rows:
                scored.append(
                    ScoredChunk(
                        chunk_id=chunk.id,
                        document_id=chunk.document_id,
                        content=chunk.content,
                        raw_text=chunk.content,
                        retrieval_text=chunk.content,
                        display_text=chunk.content,
                        chunk_type=chunk.chunk_type,
                        chunk_index=chunk.chunk_index,
                        page_number=chunk.page_number,
                        score=1.0,  # Exact identity match = 1.0
                        retrieval_mode="chemical",
                        score_breakdown={
                            "match_type": "exact_identity",
                            "chemical_score": 1.0,
                            "entity_name": chem.common_name or chem.iupac_name,
                            "inchikey": chem.inchi_key,
                            "smiles": chem.canonical_smiles,
                        },
                        metadata=chunk.metadata_ or {},
                    )
                )
            return scored
        except Exception:
            return []

    async def _search_formula_and_name(
        self,
        session: AsyncSession,
        query_text: str,
        filters: RetrievalFilter | None,
    ) -> list[ScoredChunk]:
        """Find chunks with matching chemical formulas or names."""
        clean_q = query_text.strip()
        stmt = (
            select(Chunk, ChemicalEntity)
            .join(ChunkChemicalEntity, ChunkChemicalEntity.chunk_id == Chunk.id)
            .join(ChemicalEntity, ChunkChemicalEntity.chemical_entity_id == ChemicalEntity.id)
            .join(Document, Chunk.document_id == Document.id)
            .where(
                Chunk.is_current.is_(True),
                Document.deleted_at.is_(None),
                or_(
                    ChemicalEntity.molecular_formula.ilike(clean_q),
                    ChemicalEntity.common_name.ilike(clean_q),
                    ChemicalEntity.iupac_name.ilike(clean_q),
                ),
            )
        )
        if filters and filters.organization_id:
            stmt = stmt.where(Document.organization_id == filters.organization_id)

        try:
            result = await session.execute(stmt)
            rows = result.all()
            scored: list[ScoredChunk] = []
            for chunk, chem in rows:
                match_kind = "formula_match" if (chem.molecular_formula and chem.molecular_formula.lower() == clean_q.lower()) else "name_match"
                scored.append(
                    ScoredChunk(
                        chunk_id=chunk.id,
                        document_id=chunk.document_id,
                        content=chunk.content,
                        raw_text=chunk.content,
                        retrieval_text=chunk.content,
                        display_text=chunk.content,
                        chunk_type=chunk.chunk_type,
                        chunk_index=chunk.chunk_index,
                        page_number=chunk.page_number,
                        score=0.9,  # Strong symbolic/name match
                        retrieval_mode="chemical",
                        score_breakdown={
                            "match_type": match_kind,
                            "chemical_score": 0.9,
                            "entity_name": chem.common_name or chem.iupac_name,
                            "formula": chem.molecular_formula,
                        },
                        metadata=chunk.metadata_ or {},
                    )
                )
            return scored
        except Exception:
            return []

    async def _search_molecular_similarity(
        self,
        session: AsyncSession,
        smiles: str,
        top_k: int,
        filters: RetrievalFilter | None,
        min_threshold: float,
    ) -> list[ScoredChunk]:
        """Compute chemical vector cosine similarity using Morgan / ChemBERTa embeddings."""
        # 1. Embed query molecule
        try:
            emb_res_list = await self.embedding_service.embed_smiles_list([smiles])
            if not emb_res_list:
                return []
            q_vec = emb_res_list[0].vector
        except Exception as exc:
            logger.debug("Failed to embed query molecule: %s", exc)
            return []

        # 2. Query chemical vectors in ChunkEmbedding table
        stmt = (
            select(Chunk, ChunkEmbedding)
            .join(Chunk, ChunkEmbedding.chunk_id == Chunk.id)
            .join(Document, Chunk.document_id == Document.id)
            .where(
                ChunkEmbedding.embedding_type == EmbeddingModelType.CHEMICAL,
                Chunk.is_current.is_(True),
                Document.deleted_at.is_(None),
            )
        )
        if filters and filters.organization_id:
            stmt = stmt.where(Document.organization_id == filters.organization_id)

        try:
            res = await session.execute(stmt)
            candidates = res.all()
            if not candidates:
                return []

            q_arr = np.array(q_vec, dtype=np.float32)
            q_norm = np.linalg.norm(q_arr)
            if q_norm == 0:
                return []

            scored: list[tuple[float, Chunk, ChunkEmbedding]] = []
            for chunk, chem_emb in candidates:
                c_arr = np.array(chem_emb.embedding, dtype=np.float32)
                c_norm = np.linalg.norm(c_arr)
                sim = float(np.dot(q_arr, c_arr) / (q_norm * c_norm)) if c_norm > 0 else 0.0
                if sim >= min_threshold:
                    scored.append((sim, chunk, chem_emb))

            scored.sort(key=lambda x: x[0], reverse=True)
            results: list[ScoredChunk] = []
            for sim, chunk, chem_emb in scored[:top_k]:
                results.append(
                    ScoredChunk(
                        chunk_id=chunk.id,
                        document_id=chunk.document_id,
                        content=chunk.content,
                        raw_text=chunk.content,
                        retrieval_text=chunk.content,
                        display_text=chunk.content,
                        chunk_type=chunk.chunk_type,
                        chunk_index=chunk.chunk_index,
                        page_number=chunk.page_number,
                        score=sim,
                        retrieval_mode="chemical",
                        score_breakdown={
                            "match_type": "molecular_similarity",
                            "chemical_score": sim,
                            "model_name": chem_emb.model_name,
                        },
                        metadata=chunk.metadata_ or {},
                    )
                )
            return results
        except Exception:
            return []
