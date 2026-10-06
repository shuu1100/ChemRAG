"""
ChemRAG — Storage Services Package
"""
from __future__ import annotations

from backend.app.core.config import StorageBackend, get_settings
from backend.app.services.storage.base import BaseStorageService, StorageUploadResult
from backend.app.services.storage.local import LocalStorageService


def get_storage_service() -> BaseStorageService:
    """Factory function returning the configured storage backend service."""
    settings = get_settings()
    if settings.storage.backend == StorageBackend.LOCAL:
        return LocalStorageService()
    # S3 or GCS backends can be initialized here when configured
    return LocalStorageService()


__all__ = [
    "BaseStorageService",
    "LocalStorageService",
    "StorageUploadResult",
    "get_storage_service",
]
