"""
ChemRAG — Document & Ingestion Pydantic Schemas
===============================================
Schemas for document upload, metadata responses, and ingestion job tracking.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.document import DocumentGenre, ProcessingState


class DocumentUploadResponse(BaseModel):
    """Response returned upon document upload."""
    document_id: uuid.UUID
    version_id: uuid.UUID
    status: str
    timestamp: datetime
    job_id: uuid.UUID
    filename: str
    sha256_hash: str
    file_size_bytes: int
    is_duplicate: bool = False
    message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentResponse(BaseModel):
    """Detailed document response."""
    id: uuid.UUID
    organization_id: uuid.UUID
    uploaded_by_id: Optional[uuid.UUID] = None
    filename: str
    file_size_bytes: int
    content_type: str
    doc_type: str
    genre: str
    genre_confidence: float = 0.0
    sha256_hash: str
    title: Optional[str] = None
    doi: Optional[str] = None
    journal: Optional[str] = None
    publication_year: Optional[int] = None
    abstract: Optional[str] = None
    processing_state: str
    processing_error: Optional[str] = None
    is_public: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IngestionJobResponse(BaseModel):
    """Ingestion job tracking status response."""
    id: uuid.UUID
    document_id: uuid.UUID
    organization_id: uuid.UUID
    state: str
    current_phase: Optional[str] = None
    progress_pct: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    phase_timings: Optional[Dict[str, float]] = None
    stages_completed: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)
