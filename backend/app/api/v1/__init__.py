"""
ChemRAG — API v1 Router
"""
from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.v1.endpoints.chemistry import router as chemistry_router
from backend.app.api.v1.endpoints.citations import router as citations_router
from backend.app.api.v1.endpoints.documents import router as documents_router
from backend.app.api.v1.endpoints.health import router as health_router
from backend.app.api.v1.endpoints.evaluation import router as evaluation_router
from backend.app.api.v1.endpoints.metadata import router as metadata_router
from backend.app.api.v1.endpoints.search import router as search_router

from backend.app.api.v1.endpoints.chat import router as chat_router
from backend.app.api.v1.endpoints.observability import router as observability_router

router = APIRouter()

# Health / readiness (always registered)
router.include_router(health_router, prefix="/health", tags=["Health"])

# Chat & Multi-Agent Orchestration (Phase 11 / Prompt 15.1)
router.include_router(chat_router, prefix="/chat", tags=["Chat"])

# Document ingestion & management (Phase 03)
router.include_router(documents_router, prefix="/documents", tags=["Documents"])

# Chemistry validation & entity normalization (Phase 06)
router.include_router(chemistry_router, prefix="/chemistry", tags=["Chemistry"])

# Hybrid retrieval & cross-encoder search (Phase 09 & 10)
router.include_router(search_router, prefix="/search", tags=["Search"])

# Citations and Provenance (Phase 13)
router.include_router(citations_router, prefix="/citations", tags=["Citations"])

# Scientific External Metadata (Phase 16)
router.include_router(metadata_router, prefix="/metadata", tags=["Metadata"])

# System Evaluation & RAGAS Benchmarks (Phase 17)
router.include_router(evaluation_router, prefix="/evaluation", tags=["Evaluation"])

# Observability, Telemetry & Cost Tracking (Phase 18)
router.include_router(observability_router, prefix="/observability", tags=["Observability"])
# router.include_router(agents_router,    prefix="/agents",    tags=["Agents"])      # Phase 11
# router.include_router(auth_router,      prefix="/auth",      tags=["Auth"])        # Phase 19


