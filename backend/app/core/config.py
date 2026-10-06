"""
ChemRAG — Typed Configuration System
=====================================
Uses Pydantic Settings v2 for full type-safety, validation, and
multi-environment support (development / test / production).

Every external provider exposes:
    enabled: bool
    base_url: str
    api_key: SecretStr | None
    timeout: int  (seconds)
    retries: int
    rate_limit_rpm: int
"""

from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache
from typing import Any

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ─────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────


class AppEnv(str, Enum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"


class EmbeddingProvider(str, Enum):
    OPENAI = "openai"
    SENTENCE_TRANSFORMERS = "sentence-transformers"
    MATRYOSHKA = "matryoshka"
    VOYAGE = "voyage"
    COHERE = "cohere"
    FASTEMBED = "fastembed"
    CHEMBERTA = "chemberta"
    LOCAL = "local"


class RerankerProvider(str, Enum):
    COHERE = "cohere"
    CROSS_ENCODER = "cross-encoder"
    JINA = "jina"
    BGE = "bge"
    LOCAL = "local"


class StorageBackend(str, Enum):
    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"


# ─────────────────────────────────────────────────────────
# Base provider mixin (all external services share this)
# ─────────────────────────────────────────────────────────


class ExternalProviderConfig(BaseSettings):
    """Shared fields for every external provider."""

    enabled: bool = True
    base_url: str = ""
    api_key: SecretStr | None = None
    timeout: int = Field(default=30, ge=1, le=600)
    retries: int = Field(default=3, ge=0, le=10)
    rate_limit_rpm: int = Field(default=60, ge=1)

    model_config = SettingsConfigDict(extra="ignore")


# ─────────────────────────────────────────────────────────
# Configuration Groups
# ─────────────────────────────────────────────────────────


class DatabaseConfig(BaseSettings):
    """PostgreSQL + pgvector configuration."""

    host: str = "localhost"
    port: int = Field(default=5432, ge=1, le=65535)
    db: str = "chemrag"
    user: str = "chemrag"
    password: SecretStr = SecretStr("changeme")
    pool_size: int = Field(default=10, ge=1, le=100)
    max_overflow: int = Field(default=20, ge=0, le=200)
    pool_timeout: int = Field(default=30, ge=1)
    echo: bool = False

    model_config = SettingsConfigDict(env_prefix="POSTGRES_", extra="ignore")

    @property
    def async_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.db}"
        )

    @property
    def sync_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.db}"
        )


class RedisConfig(BaseSettings):
    """Redis configuration (cache + Celery broker)."""

    host: str = "localhost"
    port: int = Field(default=6379, ge=1, le=65535)
    password: SecretStr | None = None
    db: int = Field(default=0, ge=0, le=15)
    decode_responses: bool = True
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    max_connections: int = 50

    model_config = SettingsConfigDict(env_prefix="REDIS_", extra="ignore")

    @property
    def url(self) -> str:
        password_part = (
            f":{self.password.get_secret_value()}@" if self.password else "@"
        )
        return f"redis://{password_part}{self.host}:{self.port}/{self.db}"


class StorageConfig(BaseSettings):
    """File storage configuration."""

    backend: StorageBackend = StorageBackend.LOCAL
    local_path: str = "./data/uploads"
    s3_endpoint_url: str | None = None
    s3_bucket_name: str | None = None
    s3_access_key_id: SecretStr | None = None
    s3_secret_access_key: SecretStr | None = None
    s3_region: str = "us-east-1"
    max_upload_size_mb: int = 100

    model_config = SettingsConfigDict(env_prefix="STORAGE_", extra="ignore")


class LLMConfig(BaseSettings):
    """LLM provider configuration."""

    enabled: bool = True
    provider: LLMProvider = LLMProvider.OPENAI
    base_url: str = "https://api.openai.com/v1"
    api_key: SecretStr | None = None
    model: str = "gpt-4o"
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=128000)
    timeout: int = Field(default=60, ge=1, le=600)
    retries: int = Field(default=3, ge=0, le=10)
    rate_limit_rpm: int = Field(default=500, ge=1)

    model_config = SettingsConfigDict(env_prefix="LLM_", extra="ignore")


class EmbeddingConfig(BaseSettings):
    """Embedding model configuration."""

    enabled: bool = True
    provider: EmbeddingProvider = EmbeddingProvider.OPENAI
    base_url: str = "https://api.openai.com/v1"
    api_key: SecretStr | None = None
    model: str = "text-embedding-3-large"
    dimensions: int = Field(default=3072, ge=64, le=16384)
    chemical_model: str = "deepchem/ChemBERTa-77M-MTR"
    chemical_dimensions: int = Field(default=3072, ge=64, le=16384)
    batch_size: int = Field(default=100, ge=1, le=2048)
    timeout: int = Field(default=30, ge=1, le=300)
    retries: int = Field(default=3, ge=0, le=10)
    rate_limit_rpm: int = Field(default=3000, ge=1)

    model_config = SettingsConfigDict(env_prefix="EMBEDDING_", extra="ignore")


class RerankerConfig(BaseSettings):
    """Reranker model configuration."""

    enabled: bool = True
    provider: RerankerProvider = RerankerProvider.COHERE
    base_url: str = "https://api.cohere.ai"
    api_key: SecretStr | None = None
    model: str = "rerank-english-v3.0"
    top_n: int = Field(default=5, ge=1, le=100)
    batch_size: int = Field(default=32, ge=1, le=128)
    timeout: int = Field(default=20, ge=1, le=120)
    retries: int = Field(default=3, ge=0, le=10)
    rate_limit_rpm: int = Field(default=100, ge=1)

    model_config = SettingsConfigDict(env_prefix="RERANKER_", extra="ignore")


class GROBIDConfig(BaseSettings):
    """GROBID scientific PDF parser configuration."""

    enabled: bool = True
    base_url: str = "http://localhost:8070"
    timeout: int = Field(default=120, ge=10, le=600)
    retries: int = Field(default=3, ge=0, le=10)
    rate_limit_rpm: int = Field(default=60, ge=1)
    consolidate_header: bool = True
    consolidate_citations: bool = True

    model_config = SettingsConfigDict(env_prefix="GROBID_", extra="ignore")


class DECIMERConfig(BaseSettings):
    """DECIMER chemical structure image recognition configuration."""

    enabled: bool = True
    base_url: str = "http://localhost:8082"
    timeout: int = Field(default=60, ge=5, le=300)
    retries: int = Field(default=2, ge=0, le=5)
    rate_limit_rpm: int = Field(default=30, ge=1)

    model_config = SettingsConfigDict(env_prefix="DECIMER_", extra="ignore")


class MolScribeConfig(BaseSettings):
    """MolScribe molecule image-to-SMILES configuration."""

    enabled: bool = True
    base_url: str = "http://localhost:8083"
    timeout: int = Field(default=60, ge=5, le=300)
    retries: int = Field(default=2, ge=0, le=5)
    rate_limit_rpm: int = Field(default=30, ge=1)

    model_config = SettingsConfigDict(env_prefix="MOLSCRIBE_", extra="ignore")


class PubChemConfig(BaseSettings):
    """PubChem REST API configuration for chemical normalization."""

    enabled: bool = True
    base_url: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    timeout: int = Field(default=30, ge=5, le=120)
    retries: int = Field(default=3, ge=0, le=10)
    rate_limit_rpm: int = Field(default=100, ge=1)

    model_config = SettingsConfigDict(env_prefix="PUBCHEM_", extra="ignore")


class SecurityConfig(BaseSettings):
    """JWT, authentication, and network security configuration."""

    secret_key: SecretStr = SecretStr("change-me-to-a-random-256-bit-hex-string")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, ge=5)
    refresh_token_expire_days: int = Field(default=30, ge=1)
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    bcrypt_rounds: int = Field(default=12, ge=10, le=14)

    model_config = SettingsConfigDict(env_prefix="JWT_", extra="ignore")

    @field_validator("allowed_hosts", "cors_origins", mode="before")
    @classmethod
    def split_string_list(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v


class SafetyConfig(BaseSettings):
    """Chemical safety & regulatory compliance configuration."""

    enabled: bool = True
    block_weapons_synthesis: bool = True
    block_controlled_substances: bool = True
    block_dual_use_research: bool = True
    confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    audit_all_queries: bool = True

    model_config = SettingsConfigDict(env_prefix="SAFETY_", extra="ignore")


class ObservabilityConfig(BaseSettings):
    """OpenTelemetry tracing, metrics, and structured logging."""

    otel_enabled: bool = False
    otel_exporter_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "chemrag-backend"
    otel_trace_sample_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    prometheus_enabled: bool = False
    prometheus_port: int = Field(default=9090, ge=1024, le=65535)
    log_level: str = "INFO"
    log_json: bool = False  # True in production for structured logs

    model_config = SettingsConfigDict(env_prefix="OTEL_", extra="ignore")


class EvaluationConfig(BaseSettings):
    """RAG evaluation (RAGAS + custom metrics) configuration."""

    enabled: bool = False
    dataset_path: str = "./data/eval"
    ragas_enabled: bool = False
    faithfulness_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    answer_relevancy_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    context_precision_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    run_on_startup: bool = False

    model_config = SettingsConfigDict(env_prefix="EVALUATION_", extra="ignore")


# ─────────────────────────────────────────────────────────
# Root Settings — composes all config groups
# ─────────────────────────────────────────────────────────


class Settings(BaseSettings):
    """
    Root application settings.

    Loads from environment variables and .env file.
    Environment takes precedence over .env file values.
    """

    # App-level
    app_env: AppEnv = AppEnv.DEVELOPMENT
    app_debug: bool = False
    app_log_level: str = "INFO"

    # Backend server
    backend_host: str = "0.0.0.0"
    backend_port: int = Field(default=8000, ge=1, le=65535)
    backend_workers: int = Field(default=1, ge=1, le=32)

    # Sub-config groups (instantiated lazily via properties)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def is_development(self) -> bool:
        return self.app_env == AppEnv.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        return self.app_env == AppEnv.PRODUCTION

    @property
    def is_test(self) -> bool:
        return self.app_env == AppEnv.TEST

    # ── Sub-config group factories ──
    # Each property instantiates the sub-config so it picks up the same .env

    @property
    def db(self) -> DatabaseConfig:
        return DatabaseConfig()

    @property
    def redis(self) -> RedisConfig:
        return RedisConfig()

    @property
    def storage(self) -> StorageConfig:
        return StorageConfig()

    @property
    def llm(self) -> LLMConfig:
        return LLMConfig()

    @property
    def embeddings(self) -> EmbeddingConfig:
        return EmbeddingConfig()

    @property
    def reranker(self) -> RerankerConfig:
        return RerankerConfig()

    @property
    def grobid(self) -> GROBIDConfig:
        return GROBIDConfig()

    @property
    def decimer(self) -> DECIMERConfig:
        return DECIMERConfig()

    @property
    def molscribe(self) -> MolScribeConfig:
        return MolScribeConfig()

    @property
    def pubchem(self) -> PubChemConfig:
        return PubChemConfig()

    @property
    def security(self) -> SecurityConfig:
        return SecurityConfig()

    @property
    def safety(self) -> SafetyConfig:
        return SafetyConfig()

    @property
    def observability(self) -> ObservabilityConfig:
        return ObservabilityConfig()

    @property
    def evaluation(self) -> EvaluationConfig:
        return EvaluationConfig()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached singleton Settings instance.
    In tests, call get_settings.cache_clear() then monkeypatch env vars.
    """
    return Settings()
