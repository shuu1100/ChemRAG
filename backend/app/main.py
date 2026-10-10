"""
ChemRAG — FastAPI Application Entry Point
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from backend.app.core.config import get_settings
from backend.app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup → yield → shutdown."""
    configure_logging()
    logger.info(
        "ChemRAG starting",
        env=settings.app_env.value,
        debug=settings.app_debug,
    )

    # ── Startup tasks ──────────────────────────────────────────
    try:
        from backend.app.db.base import Base
        from backend.app.db.session import get_engine, get_session_factory
        import backend.app.models  # noqa: F401
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        from sqlalchemy import text
        session_factory = get_session_factory()
        async with session_factory() as session:
            await session.execute(text("""
                INSERT INTO organizations (id, name, slug, is_active, max_documents, max_storage_bytes)
                VALUES ('00000000-0000-0000-0000-000000000000'::UUID, 'Default Organization', 'default-org', TRUE, 1000, 2147483647)
                ON CONFLICT (id) DO NOTHING;
            """))
            await session.commit()
        logger.info("Database schema initialized & default organization ready")
    except Exception as exc:
        logger.warning("Database schema initialization warning", error=str(exc))

    try:
        from backend.app.db.redis import get_redis_client
        redis_client = get_redis_client()
        await redis_client.ping()
        logger.info("Redis client initialized")
    except Exception as exc:
        logger.warning("Redis initialization warning", error=str(exc))

    try:
        from backend.app.db.health import check_database_health
        db_health = await check_database_health()
        logger.info("Database health check on startup", status=db_health.get("status"))
    except Exception as exc:
        logger.warning("Database startup check warning", error=str(exc))

    logger.info("ChemRAG started — services ready")
    yield

    # ── Shutdown tasks ─────────────────────────────────────────
    logger.info("ChemRAG shutting down")
    try:
        from backend.app.db.redis import close_redis_client
        await close_redis_client()
        logger.info("Redis client closed")
    except Exception as exc:
        logger.warning("Error closing Redis client", error=str(exc))

    try:
        from backend.app.db.session import close_engine
        await close_engine()
        logger.info("Database engine closed")
    except Exception as exc:
        logger.warning("Error closing database engine", error=str(exc))




def create_app() -> FastAPI:
    """Factory function to create the FastAPI app."""
    app = FastAPI(
        title="ChemRAG API",
        description=(
            "Chemistry-domain Retrieval-Augmented Generation system. "
            "Ingest scientific PDFs, recognize chemical structures, "
            "and answer research questions with full citation provenance."
        ),
        version="0.1.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Middleware ─────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.security.allowed_hosts,
        )

    # ── Routers ────────────────────────────────────────────────
    from backend.app.api.v1 import router as v1_router
    app.include_router(v1_router, prefix="/api/v1")

    return app


app = create_app()
