"""
Phase 01 — Configuration System Tests
======================================
Tests every configuration group for:
  - Default values load without errors
  - Env-var overrides work correctly
  - Secrets are not exposed in repr/str
  - URL property helpers produce correct strings
"""
from __future__ import annotations

import os
from typing import Generator

import pytest

from backend.app.core.config import (
    AppEnv,
    DatabaseConfig,
    DECIMERConfig,
    EmbeddingConfig,
    EmbeddingProvider,
    EvaluationConfig,
    GROBIDConfig,
    LLMConfig,
    LLMProvider,
    MolScribeConfig,
    ObservabilityConfig,
    PubChemConfig,
    RedisConfig,
    RerankerConfig,
    RerankerProvider,
    SafetyConfig,
    SecurityConfig,
    Settings,
    StorageBackend,
    StorageConfig,
    get_settings,
)


# ─────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Generator[None, None, None]:
    """Ensure a fresh Settings instance per test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ─────────────────────────────────────────────────
# Settings Root
# ─────────────────────────────────────────────────


class TestSettings:
    def test_defaults_load(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Override the test env set by conftest to check real defaults
        monkeypatch.setenv("APP_ENV", "development")
        s = Settings()
        assert s.app_env == AppEnv.DEVELOPMENT
        assert s.backend_port == 8000

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("BACKEND_PORT", "9000")
        s = Settings()
        assert s.app_env == AppEnv.PRODUCTION
        assert s.backend_port == 9000

    def test_is_development(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_ENV", "development")
        s = Settings()
        assert s.is_development is True
        assert s.is_production is False
        assert s.is_test is False

    def test_is_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_ENV", "production")
        s = Settings()
        assert s.is_production is True

    def test_is_test(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_ENV", "test")
        s = Settings()
        assert s.is_test is True

    def test_sub_configs_accessible(self) -> None:
        s = Settings()
        # All sub-configs should be instantiable without errors
        assert s.db is not None
        assert s.redis is not None
        assert s.llm is not None
        assert s.embeddings is not None
        assert s.reranker is not None
        assert s.grobid is not None
        assert s.decimer is not None
        assert s.molscribe is not None
        assert s.pubchem is not None
        assert s.security is not None
        assert s.safety is not None
        assert s.observability is not None
        assert s.evaluation is not None
        assert s.storage is not None

    def test_get_settings_cached(self) -> None:
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2  # same instance (lru_cache)


# ─────────────────────────────────────────────────
# Database Config
# ─────────────────────────────────────────────────


class TestDatabaseConfig:
    def test_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Reset any test-env overrides for db name
        monkeypatch.setenv("POSTGRES_DB", "chemrag")
        db = DatabaseConfig()
        assert db.host == "localhost"
        assert db.port == 5432
        assert db.db == "chemrag"

    def test_async_url(self) -> None:
        db = DatabaseConfig()
        assert db.async_url.startswith("postgresql+asyncpg://")
        assert "localhost" in db.async_url

    def test_sync_url(self) -> None:
        db = DatabaseConfig()
        assert db.sync_url.startswith("postgresql+psycopg://")

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("POSTGRES_HOST", "db.prod.example.com")
        monkeypatch.setenv("POSTGRES_PORT", "5433")
        db = DatabaseConfig()
        assert db.host == "db.prod.example.com"
        assert db.port == 5433

    def test_password_is_secret(self) -> None:
        db = DatabaseConfig()
        # Password must NOT appear in string representation
        assert "changeme" not in repr(db)
        assert "changeme" not in str(db)

    def test_password_accessible_via_get_secret_value(self) -> None:
        db = DatabaseConfig()
        # But should be accessible programmatically
        assert db.password.get_secret_value() is not None


# ─────────────────────────────────────────────────
# Redis Config
# ─────────────────────────────────────────────────


class TestRedisConfig:
    def test_defaults(self) -> None:
        r = RedisConfig()
        assert r.host == "localhost"
        assert r.port == 6379

    def test_url_without_password(self) -> None:
        r = RedisConfig()
        url = r.url
        assert url.startswith("redis://")
        assert "localhost" in url

    def test_url_with_password(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REDIS_PASSWORD", "supersecret")
        r = RedisConfig()
        assert "supersecret" in r.url


# ─────────────────────────────────────────────────
# LLM Config
# ─────────────────────────────────────────────────


class TestLLMConfig:
    def test_defaults(self) -> None:
        llm = LLMConfig()
        assert llm.provider == LLMProvider.OPENAI
        assert llm.enabled is True
        assert llm.temperature == pytest.approx(0.1)

    def test_temperature_bounds(self) -> None:
        with pytest.raises(Exception):
            LLMConfig(temperature=3.0)  # exceeds max

    def test_provider_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        llm = LLMConfig()
        assert llm.provider == LLMProvider.ANTHROPIC


# ─────────────────────────────────────────────────
# Embedding Config
# ─────────────────────────────────────────────────


class TestEmbeddingConfig:
    def test_defaults(self) -> None:
        e = EmbeddingConfig()
        assert e.provider == EmbeddingProvider.OPENAI
        assert e.dimensions == 3072

    def test_dimensions_bounds(self) -> None:
        with pytest.raises(Exception):
            EmbeddingConfig(dimensions=10)  # type: ignore # below minimum


# ─────────────────────────────────────────────────
# Security Config
# ─────────────────────────────────────────────────


class TestSecurityConfig:
    def test_secret_key_not_in_repr(self) -> None:
        sc = SecurityConfig()
        assert "change-me" not in repr(sc)

    def test_cors_origins_split_from_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # pydantic-settings v2 parses list fields from JSON array strings
        monkeypatch.setenv("JWT_CORS_ORIGINS", '["http://a.com", "http://b.com"]')
        sc = SecurityConfig()
        assert isinstance(sc.cors_origins, list)
        assert "http://a.com" in sc.cors_origins


# ─────────────────────────────────────────────────
# Safety Config
# ─────────────────────────────────────────────────


class TestSafetyConfig:
    def test_defaults_are_strict(self) -> None:
        s = SafetyConfig()
        assert s.enabled is True
        assert s.block_weapons_synthesis is True
        assert s.block_controlled_substances is True
        assert s.confidence_threshold >= 0.8


# ─────────────────────────────────────────────────
# External Provider Configs
# ─────────────────────────────────────────────────


class TestExternalProviders:
    def test_grobid_defaults(self) -> None:
        g = GROBIDConfig()
        assert g.enabled is True
        assert "8070" in g.base_url

    def test_decimer_defaults(self) -> None:
        d = DECIMERConfig()
        assert d.enabled is True
        assert d.retries >= 0

    def test_molscribe_defaults(self) -> None:
        m = MolScribeConfig()
        assert m.enabled is True

    def test_pubchem_defaults(self) -> None:
        p = PubChemConfig()
        assert p.enabled is True
        assert "pubchem" in p.base_url


# ─────────────────────────────────────────────────
# Observability Config
# ─────────────────────────────────────────────────


class TestObservabilityConfig:
    def test_otel_disabled_by_default(self) -> None:
        o = ObservabilityConfig()
        assert o.otel_enabled is False

    def test_sample_rate_bounds(self) -> None:
        with pytest.raises(Exception):
            ObservabilityConfig(otel_trace_sample_rate=1.5)


# ─────────────────────────────────────────────────
# Evaluation Config
# ─────────────────────────────────────────────────


class TestEvaluationConfig:
    def test_disabled_by_default(self) -> None:
        e = EvaluationConfig()
        assert e.enabled is False
        assert e.ragas_enabled is False
