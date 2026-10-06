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
    # 1. Database connection (Phase 02)
    # 2. Redis connection (Phase 02)
    # 3. Vector store initialization (Phase 08)
    # 4. LLM / Embedding model warmup (Phase 08)
    # 5. GROBID health check (Phase 03)
    # (each will be added in their respective phases)

    logger.info("ChemRAG started — all services ready")
    yield

    # ── Shutdown tasks ─────────────────────────────────────────
    logger.info("ChemRAG shutting down")


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
