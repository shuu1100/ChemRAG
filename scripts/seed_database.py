"""
ChemRAG — Database Seeding Script
=================================
Initializes database tables, enables required PostgreSQL extensions (vector, uuid-ossp, pg_trgm),
and seeds initial test/demo records into PostgreSQL.

Usage:
    python scripts/seed_database.py
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.db.base import Base
from backend.app.db.session import get_engine, get_session_factory
from backend.app.models import (
    ChemicalEntity,
    Chunk,
    ChunkEmbedding,
    Document,
    EmbeddingModelType,
    User,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_database")


async def enable_extensions(session: AsyncSession) -> None:
    """Enable PostgreSQL extensions if not already created."""
    extensions = ["vector", "uuid-ossp", "pg_trgm"]
    for ext in extensions:
        try:
            await session.execute(text(f'CREATE EXTENSION IF NOT EXISTS "{ext}";'))
            await session.commit()
            logger.info(f"Extension '{ext}' enabled/verified.")
        except Exception as exc:
            logger.warning(f"Could not enable extension '{ext}': {exc}")


async def create_tables() -> None:
    """Ensure all SQLAlchemy tables exist in database."""
    engine = get_engine()
    async with engine.begin() as conn:
        logger.info("Creating database tables if they do not exist...")
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized.")


async def seed_data(session: AsyncSession) -> None:
    """Seed initial sample chemical entities and document records."""
    # Check if sample chemical already exists
    result = await session.execute(
        text("SELECT COUNT(*) FROM chemical_entities WHERE smiles = 'CCO'")
    )
    count = result.scalar() or 0
    if count > 0:
        logger.info("Seed data already present. Skipping creation.")
        return

    logger.info("Seeding sample chemical entity and test document...")
    
    # 1. Sample Chemical Entity (Ethanol)
    ethanol = ChemicalEntity(
        id=uuid.uuid4(),
        canonical_name="Ethanol",
        smiles="CCO",
        inchikey="LFQSCWFLJHTTHZ-UHFFFAOYSA-N",
        inchi="InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3",
        formula="C2H6O",
        molecular_weight=46.07,
        iupac_name="ethanol",
    )
    session.add(ethanol)

    # 2. Sample Document
    doc = Document(
        id=uuid.uuid4(),
        title="Thermodynamic Properties of Ethanol-Water Mixtures",
        source_type="journal_article",
        file_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        file_size_bytes=102450,
        status="processed",
        metadata_={"authors": ["J. Willard Gibbs"], "year": 2024},
    )
    session.add(doc)
    await session.flush()

    # 3. Sample Chunk
    chunk_content = "Ethanol (CAS 64-17-5, formula C2H6O) is a volatile, flammable, colorless liquid with a characteristic odor."
    chunk = Chunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        chunk_index=1,
        content=chunk_content,
        content_hash="chunk_hash_001",
        contains_chemical_entities=True,
    )
    session.add(chunk)
    await session.flush()

    # 4. Sample Embedding (3072 dimensions, standard for text-embedding-3-large)
    dummy_vec = [0.01] * 3072
    chunk_emb = ChunkEmbedding(
        id=uuid.uuid4(),
        chunk_id=chunk.id,
        embedding_type=EmbeddingModelType.TEXT,
        model_name="text-embedding-3-large",
        dimensions=3072,
        embedding=dummy_vec,
    )
    session.add(chunk_emb)

    await session.commit()
    logger.info("Seeding completed successfully.")


async def main() -> None:
    logger.info("Starting ChemRAG Database Seeding process...")
    await create_tables()

    session_factory = get_session_factory()
    async with session_factory() as session:
        await enable_extensions(session)
        await seed_data(session)

    logger.info("ChemRAG Database setup & seeding complete!")


if __name__ == "__main__":
    asyncio.run(main())
