"""
ChemRAG — Structured Logging Infrastructure
============================================
Uses structlog for JSON and console logging.
Injects request ID, user ID, tenant (organization) ID, document ID,
query ID, agent run ID, latency, status, error, model, and provider contextvars.
"""
from __future__ import annotations

import logging
import sys
import uuid
from typing import Any, Dict, Optional, cast

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars
from structlog.types import EventDict, Processor

from backend.app.core.config import get_settings


def _add_log_level(logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
    event_dict["level"] = method_name.upper()
    return event_dict


def set_request_context(
    request_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    user_id: Optional[str] = None,
    document_id: Optional[str] = None,
    query_id: Optional[str] = None,
    agent_run_id: Optional[str] = None,
) -> None:
    """Bind structured context variables for log correlation."""
    bind_contextvars(
        request_id=request_id or f"req-{uuid.uuid4().hex[:10]}",
        organization_id=organization_id or "00000000-0000-0000-0000-000000000000",
        user_id=user_id,
        document_id=document_id,
        query_id=query_id,
        agent_run_id=agent_run_id,
    )


def reset_request_context() -> None:
    """Clear structured context variables after request completion."""
    clear_contextvars()


def configure_logging() -> None:
    """Configure structlog for the application."""
    settings = get_settings()
    level = getattr(logging, settings.app_log_level.upper(), logging.INFO)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        _add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.observability.log_json or settings.is_production:
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(level)

    # Reduce noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.db.echo else logging.WARNING
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
