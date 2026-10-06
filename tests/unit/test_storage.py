"""
ChemRAG — Unit Tests for Storage Services
=========================================
Tests for LocalStorageService: save, get, exists, delete, hashing, and security.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
import pytest

from backend.app.services.storage.local import LocalStorageService, sanitize_filename


class TestLocalStorageService:
    @pytest.fixture
    def temp_storage(self, tmp_path) -> LocalStorageService:
        return LocalStorageService(base_path=str(tmp_path))

    @pytest.mark.asyncio
    async def test_save_and_retrieve_file(self, temp_storage: LocalStorageService) -> None:
        content = b"%PDF-1.4 test document content for chemical analysis"
        result = await temp_storage.save(
            content=content,
            filename="paper.pdf",
            content_type="application/pdf",
            organization_id="org-123",
        )

        assert result.storage_key.startswith("org-123/")
        assert result.file_size_bytes == len(content)
        assert result.sha256_hash == hashlib.sha256(content).hexdigest()
        assert result.content_type == "application/pdf"
        assert result.local_path is not None
        assert os.path.exists(result.local_path)

        # Retrieve bytes
        retrieved = await temp_storage.get(result.storage_key)
        assert retrieved == content

    @pytest.mark.asyncio
    async def test_exists_and_delete(self, temp_storage: LocalStorageService) -> None:
        content = b"sample content"
        result = await temp_storage.save(
            content=content,
            filename="sample.pdf",
            content_type="application/pdf",
            organization_id="org-456",
        )

        assert await temp_storage.exists(result.storage_key) is True

        # Delete
        deleted = await temp_storage.delete(result.storage_key)
        assert deleted is True
        assert await temp_storage.exists(result.storage_key) is False

        # Delete again returns False
        assert await temp_storage.delete(result.storage_key) is False

    @pytest.mark.asyncio
    async def test_get_nonexistent_raises(self, temp_storage: LocalStorageService) -> None:
        with pytest.raises(FileNotFoundError):
            await temp_storage.get("org-999/nonexistent.pdf")

    def test_path_traversal_prevention(self, temp_storage: LocalStorageService) -> None:
        with pytest.raises(ValueError, match="path traversal"):
            temp_storage._resolve_key_path("../../etc/passwd")

    def test_sanitize_filename(self) -> None:
        assert sanitize_filename("../../../malicious.pdf") == "malicious.pdf"
        assert sanitize_filename("safe_name-v1.pdf") == "safe_name-v1.pdf"
        assert sanitize_filename("strange:chars*?.pdf") == "strange_chars__.pdf"
