"""
ChemRAG — Document Ingestion Endpoints
=======================================
Covers:
- POST /documents/upload  (validate, hash, dedup, store, async background ingest)
- GET  /documents/{id}     (fetch document details and classification)
- GET  /documents/jobs/{id}(fetch ingestion job status and progress)
- POST /documents/jobs/{id}/retry (resume failed ingestion job)
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger
from backend.app.db.session import get_db_session
from backend.app.models.document import (
    Document,
    DocumentGenre,
    DocumentType,
    DocumentVersion,
    ProcessingState,
)
from backend.app.models.pipeline import IngestionJob
from backend.app.schemas.document import (
    DocumentResponse,
    DocumentUploadResponse,
    IngestionJobResponse,
)
from backend.app.services.ingestion.stages import IngestionStage
from backend.app.services.ingestion.worker import (
    IngestionPipelineWorker,
    run_ingestion_background,
)
from backend.app.services.storage import get_storage_service

logger = get_logger(__name__)
router = APIRouter()
settings = get_settings()


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload PDF document for asynchronous ingestion",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF document file"),
    organization_id: uuid.UUID = Form(..., description="Tenant Organization UUID"),
    uploaded_by_id: Optional[uuid.UUID] = Form(None, description="Uploading User UUID"),
    is_public: bool = Form(False, description="Whether document is publicly accessible"),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """
    Validate, deduplicate, persist, and trigger asynchronous processing for a document.
    Does NOT parse synchronously.
    """
    filename = file.filename or "document.pdf"

    # 1. Validate file extension
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension. Only .pdf files are accepted. Received: {filename}",
        )

    # 2. Read content & enforce size limits
    content = await file.read()
    file_size_bytes = len(content)

    max_bytes = settings.storage.max_upload_size_mb * 1024 * 1024
    if file_size_bytes > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.storage.max_upload_size_mb} MB (size: {file_size_bytes:,} bytes).",
        )

    if file_size_bytes == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    # 3. Validate PDF magic bytes (%PDF-) and MIME type
    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid PDF file. Header magic bytes %PDF- not found.",
        )

    if file.content_type and file.content_type not in ("application/pdf", "application/x-pdf", "application/octet-stream"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content-type '{file.content_type}'. Must be 'application/pdf'.",
        )

    # 4. Calculate SHA-256 hash
    sha256_hash = hashlib.sha256(content).hexdigest()

    # 5. Duplicate Detection
    dup_stmt = (
        select(Document)
        .where(
            Document.sha256_hash == sha256_hash,
            Document.organization_id == organization_id,
            Document.deleted_at.is_(None),
        )
    )
    dup_result = await session.execute(dup_stmt)
    existing_doc = dup_result.scalar_one_or_none()

    if existing_doc:
        # Load latest version & job for the duplicate
        ver_stmt = (
            select(DocumentVersion)
            .where(DocumentVersion.document_id == existing_doc.id)
            .order_by(DocumentVersion.version_number.desc())
        )
        ver_res = await session.execute(ver_stmt)
        latest_ver = ver_res.scalar_one_or_none()

        job_stmt = (
            select(IngestionJob)
            .where(IngestionJob.document_id == existing_doc.id)
            .order_by(IngestionJob.created_at.desc())
        )
        job_res = await session.execute(job_stmt)
        latest_job = job_res.scalar_one_or_none()

        logger.info(
            "Duplicate document detected",
            sha256=sha256_hash,
            existing_doc_id=str(existing_doc.id),
            org_id=str(organization_id),
        )

        dup_payload = DocumentUploadResponse(
            document_id=existing_doc.id,
            version_id=latest_ver.id if latest_ver else existing_doc.id,
            status=existing_doc.processing_state.value,
            timestamp=datetime.now(timezone.utc),
            job_id=latest_job.id if latest_job else existing_doc.id,
            filename=existing_doc.filename,
            sha256_hash=existing_doc.sha256_hash,
            file_size_bytes=existing_doc.file_size_bytes,
            is_duplicate=True,
            message="Duplicate document detected. Returning existing document reference.",
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=dup_payload.model_dump(mode="json"),
        )

    # 6. Store file in persistent storage
    storage = get_storage_service()
    storage_res = await storage.save(
        content=content,
        filename=filename,
        content_type="application/pdf",
        organization_id=str(organization_id),
    )

    # 7. Create Document record
    doc = Document(
        organization_id=organization_id,
        uploaded_by_id=uploaded_by_id,
        filename=filename,
        file_size_bytes=file_size_bytes,
        content_type="application/pdf",
        doc_type=DocumentType.PDF,
        genre=DocumentGenre.UNKNOWN,
        genre_confidence=0.0,
        storage_key=storage_res.storage_key,
        sha256_hash=sha256_hash,
        processing_state=ProcessingState.PENDING,
        is_public=is_public,
    )
    session.add(doc)
    await session.flush()

    # 8. Create initial DocumentVersion
    doc_ver = DocumentVersion(
        document_id=doc.id,
        version_number=1,
        is_current=True,
        parser_name="pending",
        parser_version="1.0",
        processing_state=ProcessingState.PENDING,
    )
    session.add(doc_ver)
    await session.flush()

    # 9. Create IngestionJob record
    job = IngestionJob(
        document_id=doc.id,
        organization_id=organization_id,
        state=ProcessingState.PENDING,
        current_phase=IngestionStage.UPLOAD.value,
        progress_pct=0.0,
        config={"stages_completed": [IngestionStage.UPLOAD.value]},
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    # 10. Enqueue asynchronous background processing
    background_tasks.add_task(run_ingestion_background, job.id)

    logger.info(
        "Document uploaded and ingestion job enqueued",
        document_id=str(doc.id),
        job_id=str(job.id),
        filename=filename,
        size_bytes=file_size_bytes,
    )

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=DocumentUploadResponse(
            document_id=doc.id,
            version_id=doc_ver.id,
            status=doc.processing_state.value,
            timestamp=datetime.now(timezone.utc),
            job_id=job.id,
            filename=doc.filename,
            sha256_hash=doc.sha256_hash,
            file_size_bytes=doc.file_size_bytes,
            is_duplicate=False,
            message="Document accepted for processing.",
        ).model_dump(mode="json"),
    )


@router.get(
    "",
    response_model=list[DocumentResponse],
    summary="List all workspace documents",
)
async def list_documents(
    session: AsyncSession = Depends(get_db_session),
) -> list[DocumentResponse]:
    """Fetch all active non-deleted documents in the workspace."""
    from backend.app.models.chunk import Chunk
    from backend.app.models.document import DocumentPage
    from sqlalchemy import func

    stmt = (
        select(Document)
        .where(Document.deleted_at.is_(None))
        .order_by(Document.created_at.desc())
    )
    result = await session.execute(stmt)
    docs = result.scalars().all()

    response_list = []
    for doc in docs:
        pg_count_res = await session.execute(
            select(func.count(DocumentPage.id)).where(DocumentPage.document_id == doc.id)
        )
        pg_cnt = pg_count_res.scalar_one_or_none() or 0

        chk_count_res = await session.execute(
            select(func.count(Chunk.id)).where(Chunk.document_id == doc.id)
        )
        chk_cnt = chk_count_res.scalar_one_or_none() or 0

        response_list.append(
            DocumentResponse(
                id=doc.id,
                organization_id=doc.organization_id,
                uploaded_by_id=doc.uploaded_by_id,
                filename=doc.filename,
                file_size_bytes=doc.file_size_bytes,
                content_type=doc.content_type,
                doc_type=doc.doc_type.value,
                genre=doc.genre.value,
                genre_confidence=doc.genre_confidence,
                sha256_hash=doc.sha256_hash,
                title=doc.title,
                doi=doc.doi,
                journal=doc.journal,
                publication_year=doc.publication_year,
                abstract=doc.abstract,
                processing_state=doc.processing_state.value,
                processing_error=doc.processing_error,
                is_public=bool(doc.is_public),
                page_count=pg_cnt,
                chunk_count=chk_cnt,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )
        )

    return response_list


@router.get(
    "/jobs",
    response_model=list[IngestionJobResponse],
    summary="List all background ingestion jobs",
)
async def list_ingestion_jobs(
    session: AsyncSession = Depends(get_db_session),
) -> list[IngestionJobResponse]:
    """Fetch all ingestion jobs ordered by creation date."""
    stmt = select(IngestionJob).order_by(IngestionJob.created_at.desc())
    result = await session.execute(stmt)
    jobs = result.scalars().all()

    return [
        IngestionJobResponse(
            id=job.id,
            document_id=job.document_id,
            organization_id=job.organization_id,
            state=job.state.value,
            current_phase=job.current_phase,
            progress_pct=job.progress_pct,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            phase_timings=job.phase_timings,
            stages_completed=job.config.get("stages_completed", []) if job.config else [],
        )
        for job in jobs
    ]


@router.get(
    "/jobs/{job_id}",
    response_model=IngestionJobResponse,
    summary="Get ingestion job status and progress",
)
async def get_ingestion_job(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> IngestionJobResponse:
    """Fetch ingestion job progress, active phase, errors, and timing data."""
    stmt = select(IngestionJob).where(IngestionJob.id == job_id)
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingestion job with ID {job_id} not found.",
        )

    completed_stages = job.config.get("stages_completed", []) if job.config else []

    return IngestionJobResponse(
        id=job.id,
        document_id=job.document_id,
        organization_id=job.organization_id,
        state=job.state.value,
        current_phase=job.current_phase,
        progress_pct=job.progress_pct,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        phase_timings=job.phase_timings,
        stages_completed=completed_stages,
    )


@router.post(
    "/jobs/{job_id}/retry",
    response_model=IngestionJobResponse,
    summary="Resume or retry a failed ingestion job",
)
async def retry_ingestion_job(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
) -> IngestionJobResponse:
    """
    Resume an ingestion job from its last uncompleted stage.
    """
    stmt = select(IngestionJob).where(IngestionJob.id == job_id)
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingestion job with ID {job_id} not found.",
        )

    if job.state == ProcessingState.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job is already completed and cannot be retried.",
        )

    # Reset state to queued
    job.state = ProcessingState.QUEUED
    job.error_message = None
    job.error_traceback = None
    await session.commit()
    await session.refresh(job)

    # Enqueue background execution
    background_tasks.add_task(run_ingestion_background, job.id)

    completed_stages = job.config.get("stages_completed", []) if job.config else []

    return IngestionJobResponse(
        id=job.id,
        document_id=job.document_id,
        organization_id=job.organization_id,
        state=job.state.value,
        current_phase=job.current_phase,
        progress_pct=job.progress_pct,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        phase_timings=job.phase_timings,
        stages_completed=completed_stages,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details by ID",
)
async def get_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> DocumentResponse:
    """Fetch document metadata, genre classification, and processing status."""
    from backend.app.models.chunk import Chunk
    from backend.app.models.document import DocumentPage
    from sqlalchemy import func

    stmt = (
        select(Document)
        .where(Document.id == document_id, Document.deleted_at.is_(None))
    )
    result = await session.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )

    pg_count_res = await session.execute(
        select(func.count(DocumentPage.id)).where(DocumentPage.document_id == doc.id)
    )
    pg_cnt = pg_count_res.scalar_one_or_none() or 0

    chk_count_res = await session.execute(
        select(func.count(Chunk.id)).where(Chunk.document_id == doc.id)
    )
    chk_cnt = chk_count_res.scalar_one_or_none() or 0

    return DocumentResponse(
        id=doc.id,
        organization_id=doc.organization_id,
        uploaded_by_id=doc.uploaded_by_id,
        filename=doc.filename,
        file_size_bytes=doc.file_size_bytes,
        content_type=doc.content_type,
        doc_type=doc.doc_type.value,
        genre=doc.genre.value,
        genre_confidence=doc.genre_confidence,
        sha256_hash=doc.sha256_hash,
        title=doc.title,
        doi=doc.doi,
        journal=doc.journal,
        publication_year=doc.publication_year,
        abstract=doc.abstract,
        processing_state=doc.processing_state.value,
        processing_error=doc.processing_error,
        is_public=bool(doc.is_public),
        page_count=pg_cnt,
        chunk_count=chk_cnt,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Soft-delete document by ID",
)
async def delete_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Soft-delete document by ID."""
    stmt = (
        select(Document)
        .where(Document.id == document_id, Document.deleted_at.is_(None))
    )
    result = await session.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )

    doc.deleted_at = datetime.now(timezone.utc)
    await session.commit()
    return {"status": "deleted", "id": str(document_id)}


@router.post(
    "/{document_id}/process",
    response_model=IngestionJobResponse,
    summary="Trigger processing for a document",
)
async def process_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
) -> IngestionJobResponse:
    """Trigger or restart processing for document."""
    stmt = (
        select(Document)
        .where(Document.id == document_id, Document.deleted_at.is_(None))
    )
    result = await session.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )

    # Check for existing job or create new job
    job_stmt = (
        select(IngestionJob)
        .where(IngestionJob.document_id == document_id)
        .order_by(IngestionJob.created_at.desc())
    )
    job_res = await session.execute(job_stmt)
    job = job_res.scalar_one_or_none()

    if not job:
        job = IngestionJob(
            document_id=doc.id,
            organization_id=doc.organization_id,
            state=ProcessingState.PENDING,
            current_phase=IngestionStage.UPLOAD.value,
            progress_pct=0.0,
            config={"stages_completed": [IngestionStage.UPLOAD.value]},
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
    else:
        job.state = ProcessingState.QUEUED
        job.error_message = None
        job.config = {"stages_completed": [IngestionStage.UPLOAD.value]}
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(job, "config")
        await session.commit()
        await session.refresh(job)

    background_tasks.add_task(run_ingestion_background, job.id)

    completed_stages = job.config.get("stages_completed", []) if job.config else []
    return IngestionJobResponse(
        id=job.id,
        document_id=job.document_id,
        organization_id=job.organization_id,
        state=job.state.value,
        current_phase=job.current_phase,
        progress_pct=job.progress_pct,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        phase_timings=job.phase_timings,
        stages_completed=completed_stages,
    )


@router.get(
    "/{document_id}/status",
    summary="Get document processing status and progress",
)
async def get_document_status(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Fetch real-time document processing status and active job progress."""
    stmt = select(Document).where(Document.id == document_id, Document.deleted_at.is_(None))
    result = await session.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )

    job_stmt = select(IngestionJob).where(IngestionJob.document_id == document_id).order_by(IngestionJob.created_at.desc())
    job_res = await session.execute(job_stmt)
    job = job_res.scalar_one_or_none()

    return {
        "document_id": str(doc.id),
        "status": doc.processing_state.value,
        "processing_stage": job.current_phase if job else doc.processing_state.value,
        "progress": job.progress_pct if job else (100.0 if doc.processing_state == ProcessingState.COMPLETED else 0.0),
        "error_message": doc.processing_error or (job.error_message if job else None),
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "completed_at": job.completed_at.isoformat() if job and job.completed_at else None,
    }


@router.get(
    "/{document_id}/file",
    summary="Stream original stored PDF file",
)
async def get_document_file(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """Stream original PDF content directly from persistent storage."""
    stmt = select(Document).where(Document.id == document_id, Document.deleted_at.is_(None))
    result = await session.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )

    storage = get_storage_service()
    try:
        content = await storage.get(doc.storage_key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stored file for document could not be loaded: {str(exc)}",
        )

    from io import BytesIO
    return StreamingResponse(
        BytesIO(content),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{doc.filename}"'},
    )

