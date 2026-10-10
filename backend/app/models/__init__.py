"""
ChemRAG — Models Package
=========================
Import all models here so Alembic's autogenerate can discover them.
"""
from backend.app.db.base import Base  # noqa: F401

# User / Auth
from backend.app.models.user import Organization, User  # noqa: F401

# Documents
from backend.app.models.document import (  # noqa: F401
    Document,
    DocumentAsset,
    DocumentGenre,
    DocumentPage,
    DocumentSection,
    DocumentVersion,
)

# Chunks & Provenance
from backend.app.models.chunk import (  # noqa: F401
    Chunk,
    ChunkEmbedding,
    EmbeddingModelType,
    Provenance,
)

# Chemistry
from backend.app.models.chemical import (  # noqa: F401
    ChemicalEntity,
    ChemicalStructure,
    ChunkChemicalEntity,
)

# Tables & Experiments
from backend.app.models.table_experiment import (  # noqa: F401
    Citation,
    Experiment,
    Table,
    TableRow,
)

# Pipeline / Agent / Safety / Evaluation
from backend.app.models.pipeline import (  # noqa: F401
    AgentRun,
    AuditLog,
    EvaluationCase,
    EvaluationRun,
    IngestionJob,
    RetrievalQuery,
    RetrievalResult,
    SafetyEvent,
    ToolCall,
)

__all__ = [
    "Base",
    # User
    "Organization", "User",
    # Document
    "Document", "DocumentVersion", "DocumentPage", "DocumentAsset", "DocumentSection",
    # Chunk & Provenance
    "Chunk", "ChunkEmbedding", "Provenance",
    # Chemistry
    "ChemicalEntity", "ChemicalStructure", "ChunkChemicalEntity",
    # Tables
    "Table", "TableRow", "Experiment", "Citation",
    # Pipeline
    "IngestionJob", "RetrievalQuery", "RetrievalResult",
    "AgentRun", "ToolCall", "SafetyEvent",
    "EvaluationRun", "EvaluationCase", "AuditLog",
]
