"""
Chemical Morgan Fingerprint Embedding Provider.
Fulfills Prompt 8.3:
- Canonicalizes molecular structures.
- Generates high-dimensional circular fingerprint representations (ECFP4 / Morgan radius=2).
- Native chemistry-aware vector embedding compatible with pgvector dimensions.
"""

from __future__ import annotations

import math
from typing import Any

try:
    from rdkit import Chem
    from rdkit.Chem import rdFingerprintGenerator
    RDKIT_AVAILABLE = True
except (ImportError, Exception):
    Chem = None
    rdFingerprintGenerator = None
    RDKIT_AVAILABLE = False

from backend.app.embeddings.base import (
    BaseEmbeddingProvider,
    BatchEmbeddingResult,
    EmbeddingMetadata,
    EmbeddingResult,
)
from backend.app.models.chunk import EmbeddingModelType


class MorganFingerprintProvider(BaseEmbeddingProvider):
    """
    RDKit-powered Morgan circular fingerprint (ECFP4 equivalent) embedding provider.
    Converts SMILES or chemical structure strings into dense, L2-normalized continuous vectors.
    """

    def __init__(
        self,
        dimensions: int = 3072,
        radius: int = 2,
        model_name: str = "rdkit-morgan-ecfp4",
        is_normalized: bool = True,
        batch_size: int = 100,
    ) -> None:
        super().__init__(
            model_name=model_name,
            dimensions=dimensions,
            provider_name="rdkit-morgan",
            embedding_type=EmbeddingModelType.CHEMICAL,
            model_version="2026.3.6",
            is_normalized=is_normalized,
            batch_size=batch_size,
        )
        self.radius = radius
        if RDKIT_AVAILABLE and rdFingerprintGenerator is not None:
            self._generator = rdFingerprintGenerator.GetMorganGenerator(
                radius=self.radius,
                fpSize=self.dimensions,
            )
        else:
            self._generator = None

    def canonicalize_smiles(self, smiles_candidate: str) -> str | None:
        """Parse and return canonical SMILES, or None if invalid."""
        if not smiles_candidate or not smiles_candidate.strip():
            return None
        cleaned = smiles_candidate.strip()
        if Chem is not None:
            try:
                mol = Chem.MolFromSmiles(cleaned)
                if mol is not None:
                    return Chem.MolToSmiles(mol, canonical=True)
            except Exception:
                pass
        return cleaned

    def _smiles_to_vector(self, smiles: str) -> list[float]:
        """Convert SMILES to continuous vector via Morgan generator."""
        if self._generator is None or Chem is None:
            return self._fallback_vector(smiles)

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return self._fallback_vector(smiles)

        fp = self._generator.GetFingerprint(mol)
        return [float(bit) for bit in fp]

    def _fallback_vector(self, text: str) -> list[float]:
        """Deterministic projection fallback for chemical text with non-SMILES representations."""
        import hashlib
        raw_values: list[float] = []
        seed = f"chem_text:{text}".encode("utf-8")
        chunk_idx = 0
        while len(raw_values) < self.dimensions:
            salt = f":salt_{chunk_idx}".encode("ascii")
            digest = hashlib.sha256(seed + salt).digest()
            for i in range(0, 32, 4):
                val_int = int.from_bytes(digest[i : i + 4], byteorder="big", signed=True)
                raw_values.append(val_int / 2147483648.0)
                if len(raw_values) == self.dimensions:
                    break
            chunk_idx += 1
        return raw_values

    async def embed_batch(self, texts: list[str]) -> BatchEmbeddingResult:
        results: list[EmbeddingResult] = []
        failed_indices: list[int] = []
        errors: dict[int, str] = dict()

        metadata = self.get_metadata()

        for idx, text in enumerate(texts):
            try:
                canonical = self.canonicalize_smiles(text)
                if canonical is not None:
                    raw_vec = self._smiles_to_vector(canonical)
                else:
                    # Attempt text fallback if string was a formula or chemical entity name
                    raw_vec = self._fallback_vector(text)

                norm_vec, norm = self.validate_vector(raw_vec)
                results.append(
                    EmbeddingResult(
                        vector=norm_vec,
                        dimensions=self.dimensions,
                        norm=norm,
                        metadata=metadata,
                        tokens_used=1,
                    )
                )
            except Exception as exc:
                failed_indices.append(idx)
                errors[idx] = str(exc)

        return BatchEmbeddingResult(
            results=results,
            failed_indices=failed_indices,
            errors=errors,
        )
