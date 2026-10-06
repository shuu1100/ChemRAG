"""
ChemRAG — Abstract Storage Interface
=====================================
Unified interface for file storage backends (Local filesystem, S3/MinIO, GCS).
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import AsyncGenerator, BinaryIO


@dataclass(frozen=True)
class StorageUploadResult:
    """Result metadata returned after saving a file to storage."""
    storage_key: str
    file_size_bytes: int
    sha256_hash: str
    content_type: str
    local_path: str | None = None


class BaseStorageService(abc.ABC):
    """Abstract file storage service."""

    @abc.abstractmethod
    async def save(
        self,
        content: bytes,
        filename: str,
        content_type: str,
        organization_id: str,
    ) -> StorageUploadResult:
        """
        Persist a file and calculate its hash, size, and storage key.
        """
        ...

    @abc.abstractmethod
    async def get(self, storage_key: str) -> bytes:
        """Retrieve the raw bytes of a stored file."""
        ...

    @abc.abstractmethod
    async def exists(self, storage_key: str) -> bool:
        """Check if a file exists in storage."""
        ...

    @abc.abstractmethod
    async def delete(self, storage_key: str) -> bool:
        """Remove a file from storage. Returns True if deleted, False if not found."""
        ...

    @abc.abstractmethod
    def get_file_path(self, storage_key: str) -> str | None:
        """Return the local filesystem path if available, or None if remote."""
        ...
