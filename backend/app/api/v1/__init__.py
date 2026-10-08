"""
ChemRAG — API v1 Router
"""
from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.v1.endpoints.chemistry import router as chemistry_router
from backend.app.api.v1.endpoints.citations import router as citations_router
from backend.app.api.v1.endpoints.documents import router as documents_router
from backend.app.api.v1.endpoints.health import router as health_router
from backend.app.api.v1.endpoints.search import router as search_router

router = APIRouter()

# Health / readiness (always registered)
router.include_router(health_router, prefix="/health", tags=["Health"])

# Document ingestion & management (Phase 03)
router.include_router(documents_router, prefix="/documents", tags=["Documents"])

# Chemistry validation & entity normalization (Phase 06)
router.include_router(chemistry_router, prefix="/chemistry", tags=["Chemistry"])

# Hybrid retrieval & cross-encoder search (Phase 09 & 10)
router.include_router(search_router, prefix="/search", tags=["Search"])

# Citations and Provenance (Phase 13)
router.include_router(citations_router, prefix="/citations", tags=["Citations"])
# router.include_router(agents_router,    prefix="/agents",    tags=["Agents"])      # Phase 11
# router.include_router(auth_router,      prefix="/auth",      tags=["Auth"])        # Phase 19


