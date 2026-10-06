"""
ChemRAG — Unit Tests for Ingestion Worker & Pipeline
=====================================================
Tests:
- Strict pipeline sequence
- Idempotency & stage tracking
- Simulated stage failure
- Resumption from failed stage
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from backend.app.models.document import Document, DocumentGenre, DocumentType, ProcessingState
from backend.app.models.pipeline import IngestionJob
from backend.app.services.document_classifier import ClassificationResult, DocumentClassifier
from backend.app.services.ingestion.stages import (
    STAGE_SEQUENCE,
    IngestionStage,
    calculate_progress_pct,
    get_next_stage,
    get_stage_index,
)
from backend.app.services.ingestion.worker import IngestionPipelineWorker


class TestIngestionStages:
    def test_strict_stage_sequence(self) -> None:
        expected = [
            IngestionStage.UPLOAD,
            IngestionStage.VALIDATE,
            IngestionStage.STORE,
            IngestionStage.CLASSIFY,
            IngestionStage.PARSE,
            IngestionStage.EXTRACT,
            IngestionStage.NORMALIZE,
            IngestionStage.CHUNK,
            IngestionStage.EMBED,
            IngestionStage.INDEX,
            IngestionStage.COMPLETE,
        ]
        assert STAGE_SEQUENCE == expected

    def test_stage_index_and_next(self) -> None:
        assert get_stage_index(IngestionStage.UPLOAD) == 0
        assert get_stage_index(IngestionStage.COMPLETE) == 10
        assert get_next_stage(IngestionStage.UPLOAD) == IngestionStage.VALIDATE
        assert get_next_stage(IngestionStage.INDEX) == IngestionStage.COMPLETE
        assert get_next_stage(IngestionStage.COMPLETE) is None

    def test_calculate_progress_pct(self) -> None:
        assert calculate_progress_pct(IngestionStage.UPLOAD) == 0.0
        assert calculate_progress_pct(IngestionStage.COMPLETE) == 100.0
        assert calculate_progress_pct(IngestionStage.CLASSIFY) == 30.0


class TestIngestionPipelineWorker:
    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock()
        session.commit = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def sample_document(self) -> Document:
        doc = Document(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            filename="benzene_study.pdf",
            file_size_bytes=1024,
            content_type="application/pdf",
            doc_type=DocumentType.PDF,
            genre=DocumentGenre.UNKNOWN,
            storage_key="test/benzene_study.pdf",
            sha256_hash="abc123hash",
            processing_state=ProcessingState.PENDING,
        )
        return doc

    @pytest.fixture
    def sample_job(self, sample_document: Document) -> IngestionJob:
        job = IngestionJob(
            id=uuid.uuid4(),
            document_id=sample_document.id,
            organization_id=sample_document.organization_id,
            state=ProcessingState.PENDING,
            current_phase=IngestionStage.UPLOAD.value,
            progress_pct=0.0,
            config={"stages_completed": [IngestionStage.UPLOAD.value]},
        )
        return job

    @pytest.mark.asyncio
    async def test_worker_completes_all_stages(
        self,
        mock_session: AsyncMock,
        sample_document: Document,
        sample_job: IngestionJob,
    ) -> None:
        # Mock session.execute to return job and doc
        job_result = MagicMock()
        job_result.scalar_one_or_none.return_value = sample_job
        doc_result = MagicMock()
        doc_result.scalar_one_or_none.return_value = sample_document

        mock_session.execute.side_effect = [job_result, doc_result]

        worker = IngestionPipelineWorker()
        worker.storage = AsyncMock()
        worker.storage.exists = AsyncMock(return_value=True)
        worker.storage.get = AsyncMock(return_value=b"%PDF-1.4 sample content with abstract and doi")

        completed_job = await worker.execute_job(sample_job.id, mock_session)

        assert completed_job.state == ProcessingState.COMPLETED
        assert completed_job.current_phase == IngestionStage.COMPLETE.value
        assert completed_job.progress_pct == 100.0
        assert completed_job.completed_at is not None
        assert sample_document.processing_state == ProcessingState.COMPLETED
        # All stages recorded in stages_completed
        assert len(completed_job.config["stages_completed"]) == len(STAGE_SEQUENCE)

    @pytest.mark.asyncio
    async def test_worker_fails_and_records_state(
        self,
        mock_session: AsyncMock,
        sample_document: Document,
        sample_job: IngestionJob,
    ) -> None:
        job_result = MagicMock()
        job_result.scalar_one_or_none.return_value = sample_job
        doc_result = MagicMock()
        doc_result.scalar_one_or_none.return_value = sample_document

        mock_session.execute.side_effect = [job_result, doc_result]

        worker = IngestionPipelineWorker()
        worker.storage = AsyncMock()
        worker.storage.exists = AsyncMock(return_value=True)
        worker.storage.get = AsyncMock(return_value=b"%PDF-1.4 content")

        with pytest.raises(RuntimeError, match="Simulated pipeline failure at stage: EXTRACT"):
            await worker.execute_job(
                sample_job.id,
                mock_session,
                fail_at_stage=IngestionStage.EXTRACT,
            )

        assert sample_job.state == ProcessingState.FAILED
        assert sample_job.current_phase == IngestionStage.EXTRACT.value
        assert "Simulated pipeline failure" in sample_job.error_message
        assert sample_job.error_traceback is not None
        assert sample_document.processing_state == ProcessingState.FAILED

    @pytest.mark.asyncio
    async def test_worker_resumes_from_failed_stage(
        self,
        mock_session: AsyncMock,
        sample_document: Document,
        sample_job: IngestionJob,
    ) -> None:
        """
        Job was previously failed at EXTRACT. It already has stages completed up to PARSE.
        When resumed, it skips UPLOAD..PARSE, executes from EXTRACT, and completes.
        """
        # Prior state: completed up to PARSE
        stages_done = [
            IngestionStage.UPLOAD.value,
            IngestionStage.VALIDATE.value,
            IngestionStage.STORE.value,
            IngestionStage.CLASSIFY.value,
            IngestionStage.PARSE.value,
        ]
        sample_job.config = {"stages_completed": stages_done}
        sample_job.state = ProcessingState.FAILED
        sample_job.current_phase = IngestionStage.EXTRACT.value

        job_result = MagicMock()
        job_result.scalar_one_or_none.return_value = sample_job
        doc_result = MagicMock()
        doc_result.scalar_one_or_none.return_value = sample_document

        mock_session.execute.side_effect = [job_result, doc_result]

        worker = IngestionPipelineWorker()
        worker.storage = AsyncMock()
        worker.storage.exists = AsyncMock(return_value=True)
        worker.storage.get = AsyncMock(return_value=b"%PDF-1.4 content")

        resumed_job = await worker.execute_job(sample_job.id, mock_session)

        assert resumed_job.state == ProcessingState.COMPLETED
        assert resumed_job.current_phase == IngestionStage.COMPLETE.value
        assert resumed_job.progress_pct == 100.0
        assert len(resumed_job.config["stages_completed"]) == len(STAGE_SEQUENCE)
