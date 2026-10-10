"""
ChemRAG — Experimental Records API Endpoints
================================================
Endpoints:
- GET  /experiments          (List extracted experimental records from PostgreSQL with filtering)
- GET  /experiments/{id}     (Get detailed experimental record by ID)
- POST /experiments/extract/{document_id} (Trigger extraction on a document)
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.models.document import Document
from backend.app.models.table_experiment import Experiment
from backend.app.services.experiment_extractor import ExperimentExtractor
from backend.app.services.storage import get_storage_service

router = APIRouter()


class ExperimentResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    document_title: Optional[str] = None
    description: Optional[str] = None
    experimental_conditions: Optional[Dict[str, Any]] = None
    results: Optional[Dict[str, Any]] = None
    chemical_participants: Optional[List[Any]] = None
    confidence: Optional[float] = 0.85
    created_at: Optional[str] = None


@router.get(
    "",
    response_model=List[ExperimentResponse],
    summary="List extracted experimental records",
)
async def list_experiments(
    chemical: Optional[str] = Query(None, description="Filter by chemical substance name or formula"),
    solvent: Optional[str] = Query(None, description="Filter by solvent"),
    catalyst: Optional[str] = Query(None, description="Filter by catalyst"),
    session: AsyncSession = Depends(get_db_session),
) -> List[ExperimentResponse]:
    """Fetch experimental records stored in PostgreSQL database with optional filtering."""
    stmt = select(Experiment, Document.title).join(Document, Experiment.document_id == Document.id).order_by(Experiment.created_at.desc())
    result = await session.execute(stmt)
    rows = result.all()

    items: List[ExperimentResponse] = []
    for exp, doc_title in rows:
        conds = exp.experimental_conditions or {}
        participants = exp.chemical_participants or []

        # Apply filters
        if solvent and solvent.lower() not in str(conds.get("solvent", "")).lower():
            continue
        if catalyst and catalyst.lower() not in str(conds.get("catalyst", "")).lower():
            continue
        if chemical:
            chem_str = f"{exp.description or ''} {str(participants)} {str(conds)}".lower()
            if chemical.lower() not in chem_str:
                continue

        items.append(
            ExperimentResponse(
                id=exp.id,
                document_id=exp.document_id,
                document_title=doc_title or "Scientific Paper",
                description=exp.description,
                experimental_conditions=exp.experimental_conditions,
                results=exp.results,
                chemical_participants=exp.chemical_participants,
                confidence=exp.confidence or 0.85,
                created_at=exp.created_at.isoformat() if exp.created_at else None,
            )
        )

    return items


@router.get(
    "/{experiment_id}",
    response_model=ExperimentResponse,
    summary="Get experimental record by ID",
)
async def get_experiment(
    experiment_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ExperimentResponse:
    """Fetch detail for a single experimental record."""
    stmt = select(Experiment, Document.title).join(Document, Experiment.document_id == Document.id).where(Experiment.id == experiment_id)
    result = await session.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment record '{experiment_id}' not found.",
        )
    exp, doc_title = row
    return ExperimentResponse(
        id=exp.id,
        document_id=exp.document_id,
        document_title=doc_title or "Scientific Paper",
        description=exp.description,
        experimental_conditions=exp.experimental_conditions,
        results=exp.results,
        chemical_participants=exp.chemical_participants,
        confidence=exp.confidence or 0.85,
        created_at=exp.created_at.isoformat() if exp.created_at else None,
    )


@router.post(
    "/extract/{document_id}",
    response_model=List[ExperimentResponse],
    summary="Extract and save experimental records for a document",
)
async def extract_experiments_for_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> List[ExperimentResponse]:
    """Trigger experimental data extraction from a document's text into PostgreSQL."""
    stmt = select(Document).where(Document.id == document_id)
    res = await session.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    storage = get_storage_service()
    try:
        pdf_bytes = await storage.get(doc.storage_key)
        text = pdf_bytes[:50000].decode("latin-1", errors="ignore")
    except Exception:
        text = f"{doc.title or ''}\n{doc.abstract or ''}"

    extractor = ExperimentExtractor()
    extracted_records = extractor.extract_from_text(text)

    created: List[ExperimentResponse] = []
    for rec in extracted_records:
        exp_model = Experiment(
            id=uuid.uuid4(),
            document_id=doc.id,
            description=rec.description,
            experimental_conditions={
                "temperature_celsius": rec.temperature_celsius,
                "pressure_bar": rec.pressure_bar,
                "solvent": rec.solvent,
                "catalyst": rec.catalyst,
                "reaction_time_hours": rec.reaction_time_hours,
            },
            results={
                "yield_percentage": rec.yield_percentage,
            },
            chemical_participants=[
                {"role": "reactant", "name": r} for r in rec.reactants
            ] + [
                {"role": "product", "name": p} for p in rec.products
            ],
            confidence=rec.confidence,
        )
        session.add(exp_model)
        await session.flush()

        created.append(
            ExperimentResponse(
                id=exp_model.id,
                document_id=doc.id,
                document_title=doc.title or doc.filename,
                description=exp_model.description,
                experimental_conditions=exp_model.experimental_conditions,
                results=exp_model.results,
                chemical_participants=exp_model.chemical_participants,
                confidence=exp_model.confidence,
                created_at=exp_model.created_at.isoformat() if exp_model.created_at else None,
            )
        )

    await session.commit()
    return created
