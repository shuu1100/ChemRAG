"""
Shared pytest configuration for ChemRAG.
"""
from __future__ import annotations

import os

import pytest

# ── Test environment defaults ──────────────────────────────────────────────
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "chemrag_test")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "integration: marks tests that require Docker services"
    )
    config.addinivalue_line(
        "markers", "e2e: marks end-to-end tests"
    )
