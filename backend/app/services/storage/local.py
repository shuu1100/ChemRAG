"""
ChemRAG — Local Filesystem Storage Backend
===========================================
Stores uploaded documents on the local filesystem partitioned by organization and hash.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger
from backend.app.services.storage.base import BaseStorageService, StorageUploadResult

logger = get_logger(__name__)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal or invalid characters."""
    clean = os.path.basename(filename)
    clean = re.sub(r"[^\w\.\-\_]", "_", clean)
    return clean or "unnamed_file"


class LocalStorageService(BaseStorageService):
    """Local disk storage implementation."""

    def __init__(self, base_path: str | None = None) -> None:
        settings = get_settings()
        self.base_dir = Path(base_path or settings.storage.local_path).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_key_path(self, storage_key: str) -> Path:
        """Resolve a storage key to an absolute Path, preventing traversal."""
        full_path = (self.base_dir / storage_key).resolve()
        if not str(full_path).startswith(str(self.base_dir)):
            raise ValueError(f"Invalid storage key path traversal: {storage_key}")
        return full_path

    async def save(
        self,
        content: bytes,
        filename: str,
        content_type: str,
        organization_id: str,
    ) -> StorageUploadResult:
        sha256 = hashlib.sha256(content).hexdigest()
        file_size = len(content)
        safe_name = sanitize_filename(filename)

        # Partition: {org_id}/{sha_prefix_2}/{sha256}_{filename}
        prefix = sha256[:2]
        rel_key = f"{organization_id}/{prefix}/{sha256}_{safe_name}"
        dest_path = self.base_dir / rel_key
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file atomically via temp write or direct
        dest_path.write_bytes(content)
        logger.info(
            "File saved to local storage",
            storage_key=rel_key,
            size_bytes=file_size,
            sha256=sha256,
        )

        return StorageUploadResult(
            storage_key=rel_key,
            file_size_bytes=file_size,
            sha256_hash=sha256,
            content_type=content_type,
            local_path=str(dest_path),
        )

    async def get(self, storage_key: str) -> bytes:
        file_path = self._resolve_key_path(storage_key)
        if not file_path.exists():
            raise FileNotFoundError(f"Storage object not found: {storage_key}")
        return file_path.read_bytes()

    async def exists(self, storage_key: str) -> bool:
        file_path = self._resolve_key_path(storage_key)
        return file_path.exists() and file_path.is_file()

    async def delete(self, storage_key: str) -> bool:
        file_path = self._resolve_key_path(storage_key)
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            return True
        return False

    def get_file_path(self, storage_key: str) -> str | None:
        file_path = self._resolve_key_path(storage_key)
        if file_path.exists():
            return str(file_path)
        return None
