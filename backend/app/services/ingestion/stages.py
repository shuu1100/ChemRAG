"""
ChemRAG — Ingestion Pipeline Stages
===================================
Defines the strictly ordered stages of the ingestion worker pipeline:
UPLOAD -> VALIDATE -> STORE -> CLASSIFY -> PARSE -> EXTRACT -> NORMALIZE -> CHUNK -> EMBED -> INDEX -> COMPLETE.
"""
from __future__ import annotations

import enum
from typing import List, Optional


class IngestionStage(str, enum.Enum):
    UPLOAD = "UPLOAD"
    VALIDATE = "VALIDATE"
    STORE = "STORE"
    CLASSIFY = "CLASSIFY"
    PARSE = "PARSE"
    EXTRACT = "EXTRACT"
    NORMALIZE = "NORMALIZE"
    CHUNK = "CHUNK"
    EMBED = "EMBED"
    INDEX = "INDEX"
    COMPLETE = "COMPLETE"


STAGE_SEQUENCE: List[IngestionStage] = [
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


def get_stage_index(stage: IngestionStage) -> int:
    """Return 0-indexed position of a stage."""
    return STAGE_SEQUENCE.index(stage)


def get_next_stage(stage: IngestionStage) -> Optional[IngestionStage]:
    """Return the next stage in the pipeline or None if complete."""
    idx = get_stage_index(stage)
    if idx + 1 < len(STAGE_SEQUENCE):
        return STAGE_SEQUENCE[idx + 1]
    return None


def calculate_progress_pct(stage: IngestionStage) -> float:
    """Calculate progress percentage based on stage reached."""
    idx = get_stage_index(stage)
    return round((idx / (len(STAGE_SEQUENCE) - 1)) * 100.0, 1)
