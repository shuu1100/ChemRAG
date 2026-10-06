"""
ChemRAG — API v1 Router
"""
from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.v1.endpoints.health import router as health_router

router = APIRouter()

# Health / readiness (always registered)
router.include_router(health_router, prefix="/health", tags=["Health"])

# Future phases will add routers here:
# router.include_router(documents_router, prefix="/documents", tags=["Documents"])   # Phase 03
# router.include_router(search_router,    prefix="/search",    tags=["Search"])      # Phase 09
# router.include_router(agents_router,    prefix="/agents",    tags=["Agents"])      # Phase 11
# router.include_router(auth_router,      prefix="/auth",      tags=["Auth"])        # Phase 19
