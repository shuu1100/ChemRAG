"""
ChemRAG — SQLAlchemy Declarative Base
"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase, MappedColumn


class Base(DeclarativeBase):
    """Root declarative base for all ORM models."""
    pass
