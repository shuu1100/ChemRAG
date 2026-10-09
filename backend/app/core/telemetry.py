"""
ChemRAG — OpenTelemetry Tracing Infrastructure
==============================================
Provides OpenTelemetry-ready distributed tracing spans across system boundaries:
- API requests
- Hybrid & vector retrieval
- Database queries
- Embeddings generation
- Cohere & cross-encoder reranking
- Multi-agent orchestration
- RDKit chemical validation
- External API calls (PubChem, Crossref, etc.)
- LLM inference calls
- Citation entailment validation
"""
from __future__ import annotations

import asyncio
import functools
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TraceSpan:
    """Individual OpenTelemetry-compatible span object."""
    span_id: str
    name: str
    kind: str = "INTERNAL"
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    status: str = "OK"
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    def finish(self, status: str = "OK", error: Optional[str] = None) -> None:
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000.0
        self.status = status
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "name": self.name,
            "kind": self.kind,
            "duration_ms": round(self.duration_ms, 2),
            "status": self.status,
            "attributes": self.attributes,
            "error": self.error,
        }


class TelemetryTracer:
    """OpenTelemetry-compatible tracer and span manager."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._active_spans: List[TraceSpan] = []
        self._span_counter = 0

    @contextmanager
    def start_span(
        self,
        name: str,
        kind: str = "INTERNAL",
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """Context manager for tracing operations."""
        self._span_counter += 1
        span_id = f"span-{self._span_counter}-{int(time.time()*1000)}"
        span = TraceSpan(
            span_id=span_id,
            name=name,
            kind=kind,
            attributes=attributes or {},
        )
        self._active_spans.append(span)

        try:
            yield span
            span.finish(status="OK")
        except Exception as exc:
            span.finish(status="ERROR", error=str(exc))
            raise
        finally:
            logger.debug(
                "Trace span completed",
                span_name=name,
                duration_ms=span.duration_ms,
                status=span.status,
            )

    def get_recent_spans(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recently recorded trace spans."""
        return [s.to_dict() for s in self._active_spans[-limit:]]


# Global tracer instance
tracer = TelemetryTracer()


def trace_operation(name: str, kind: str = "INTERNAL"):
    """Decorator for tracing sync/async functions."""
    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                with tracer.start_span(name=name, kind=kind):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                with tracer.start_span(name=name, kind=kind):
                    return func(*args, **kwargs)
            return sync_wrapper
    return decorator
