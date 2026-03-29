"""Core tracing logic: Tracer, SpanData, context management."""
import functools
import inspect
import logging
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol, runtime_checkable

from .transport import post_spans, post_trace

logger = logging.getLogger("agentlens")

_current_trace: ContextVar[Optional["ActiveTrace"]] = ContextVar(
    "_current_trace", default=None
)


@runtime_checkable
class SpanExporter(Protocol):
    """Protocol for optional span exporters (e.g. OpenTelemetry)."""

    def export_span(self, span_data: "SpanData") -> None:
        """Called after each span completes. Must not raise."""
        ...

    def shutdown(self) -> None:
        """Called when the process is done. Flush any pending state."""
        ...


@runtime_checkable
class SpanProcessor(Protocol):
    """Protocol for span lifecycle hooks — modify or observe spans in-flight."""

    def on_start(self, span: "SpanData") -> None:
        """Called when a span starts (pushed to stack). Must not raise."""
        ...

    def on_end(self, span: "SpanData") -> None:
        """Called when a span ends (popped from stack). Must not raise."""
        ...


# Global registries — populated via Tracer.add_exporter() / add_processor()
_exporters: list[SpanExporter] = []
_processors: list[SpanProcessor] = []


def _emit_to_exporters(span: "SpanData") -> None:
    """Forward a completed span to all registered exporters. Never raises."""
    for exporter in _exporters:
        try:
            exporter.export_span(span)
        except Exception as exc:
            logger.debug("AgentLens exporter error (non-fatal): %s", exc)


def _notify_processors_start(span: "SpanData") -> None:
    """Notify processors when a span starts. Never raises."""
    for proc in _processors:
        try:
            proc.on_start(span)
        except Exception as exc:
            logger.debug("AgentLens processor on_start error (non-fatal): %s", exc)


def _notify_processors_end(span: "SpanData") -> None:
    """Notify processors when a span ends. Never raises."""
    for proc in _processors:
        try:
            proc.on_end(span)
        except Exception as exc:
            logger.debug("AgentLens processor on_end error (non-fatal): %s", exc)


@dataclass
class SpanData:
    span_id: str
    parent_id: Optional[str]
    name: str
    type: str
    start_ms: int
    end_ms: Optional[int] = None
    input: Optional[str] = None
    output: Optional[str] = None
    cost: Optional[dict] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "type": self.type,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "input": self.input,
            "output": self.output,
            "cost": self.cost,
            "metadata": self.metadata,
        }


class ActiveTrace:
    def __init__(self, trace_id: str, agent_name: str, streaming: bool = False):
        self.trace_id = trace_id
        self.agent_name = agent_name
        self.streaming = streaming
        self.spans: list[SpanData] = []
        self._span_stack: list[str] = []  # stack of span_ids

    def current_span_id(self) -> Optional[str]:
        return self._span_stack[-1] if self._span_stack else None

    def push_span(self, span: SpanData):
        self.spans.append(span)
        self._span_stack.append(span.span_id)
        _notify_processors_start(span)

    def pop_span(self, span: Optional[SpanData] = None):
        if self._span_stack:
            self._span_stack.pop()
        if span:
            _notify_processors_end(span)

    def flush_span(self, span: SpanData) -> None:
        """Send a single completed span immediately (streaming mode only)."""
        _emit_to_exporters(span)
        if self.streaming:
            post_spans(self.trace_id, [span.to_dict()])

    def flush(self):
        """Send the full trace batch. Always works regardless of streaming mode."""
        # Export every span to registered exporters
        for span in self.spans:
            _emit_to_exporters(span)
        spans = [s.to_dict() for s in self.spans]
        post_trace(self.trace_id, self.agent_name, spans)


class SpanContext:
    """Context manager for manual spans."""

    def __init__(self, active: ActiveTrace, span: SpanData):
        self._active = active
        self._span = span

    def set_output(self, output: str):
        self._span.output = str(output)[:4096]

    def set_cost(self, model: str, input_tokens: int, output_tokens: int,
                 usd: Optional[float] = None):
        from .cost import calculate_cost
        self._span.cost = {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "usd": usd if usd is not None else calculate_cost(model, input_tokens, output_tokens),
        }

    def set_metadata(self, **kwargs):
        self._span.metadata.update(kwargs)

    def log(self, message: str, **extra) -> None:
        """Add a timestamped note to this span's metadata.

        Args:
            message: Human-readable note.
            **extra: Additional key/value pairs merged into the log entry.
        """
        logs: list = self._span.metadata.setdefault("logs", [])
        entry: dict = {"ts_ms": _now_ms(), "message": str(message)[:1024]}
        entry.update({k: v for k, v in extra.items()})
        logs.append(entry)

    def __enter__(self):
        self._active.push_span(self._span)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._span.end_ms = _now_ms()
        self._active.pop_span(self._span)
        # In streaming mode, push completed span to server immediately
        self._active.flush_span(self._span)
        return False  # don't suppress exceptions


def _now_ms() -> int:
    return int(time.time() * 1000)


def _str_truncate(v: Any, limit: int = 4096) -> Optional[str]:
    if v is None:
        return None
    return str(v)[:limit]


class _NoopSpanContext:
    """Returned when span() called outside a trace — silently does nothing."""
    def set_output(self, *a, **kw): pass
    def set_cost(self, *a, **kw): pass
    def set_metadata(self, **kw): pass
    def log(self, message: str, **extra): pass
    def __enter__(self): return self
    def __exit__(self, *a): return False


class Tracer:
    """Main SDK entry point. One instance shared globally."""

    def __init__(self):
        self._server_url: Optional[str] = None
        self._streaming: bool = False

    def configure(
        self,
        server_url: str,
        api_key: Optional[str] = None,
        streaming: bool = False,
        batch: bool = False,
        batch_max_size: int = 10,
        batch_flush_interval: float = 5.0,
    ):
        """Configure server URL and transport options.

        Args:
            server_url: Base URL of the AgentLens server.
            api_key: API key for authentication (X-API-Key header).
            streaming: When True, completed spans are sent immediately as they
                       finish rather than waiting for the full trace to complete.
            batch: When True, traces are queued and flushed in batches.
            batch_max_size: Flush batch when this many traces accumulate.
            batch_flush_interval: Auto-flush batch every N seconds.
        """
        self._server_url = server_url
        self._streaming = streaming
        if api_key:
            from .transport import set_api_key
            set_api_key(api_key)
        if batch:
            from .transport import configure_batch
            configure_batch(
                enabled=True,
                server_url=server_url,
                max_size=batch_max_size,
                flush_interval=batch_flush_interval,
            )

    def add_processor(self, processor: SpanProcessor) -> None:
        """Register a span processor for lifecycle hooks.

        Processors receive on_start/on_end calls for every span,
        allowing observation or modification of spans in-flight.

        Args:
            processor: Any object implementing the SpanProcessor protocol.
        """
        _processors.append(processor)

    def add_exporter(self, exporter: SpanExporter) -> None:
        """Register an optional span exporter (e.g. OTel).

        Exporters receive every completed span in addition to the normal
        AgentLens HTTP transport.  Multiple exporters can be registered.

        Args:
            exporter: Any object implementing the SpanExporter protocol.
        """
        _exporters.append(exporter)

    def trace(self, func: Optional[Callable] = None, *, name: Optional[str] = None,
              span_type: str = "agent_run"):
        """Decorator for sync or async agent functions."""
        def decorator(fn: Callable) -> Callable:
            agent_name = name or fn.__name__

            if inspect.iscoroutinefunction(fn):
                @functools.wraps(fn)
                async def async_wrapper(*args, **kwargs):
                    return await self._run_async(fn, agent_name, span_type, args, kwargs)
                return async_wrapper
            else:
                @functools.wraps(fn)
                def sync_wrapper(*args, **kwargs):
                    return self._run_sync(fn, agent_name, span_type, args, kwargs)
                return sync_wrapper

        if func is not None:  # called as @trace (no parens)
            return decorator(func)
        return decorator  # called as @trace(name="...")

    def _run_sync(self, fn, agent_name, span_type, args, kwargs):
        active = ActiveTrace(str(uuid.uuid4()), agent_name, streaming=self._streaming)
        token = _current_trace.set(active)
        root = SpanData(
            span_id=str(uuid.uuid4()),
            parent_id=None,
            name=agent_name,
            type=span_type,
            start_ms=_now_ms(),
            input=_str_truncate(args[0] if args else kwargs),
        )
        active.push_span(root)
        try:
            result = fn(*args, **kwargs)
            root.output = _str_truncate(result)
            return result
        except Exception as exc:
            root.metadata["error"] = str(exc)
            raise
        finally:
            root.end_ms = _now_ms()
            active.pop_span(root)
            active.flush()
            _current_trace.reset(token)

    async def _run_async(self, fn, agent_name, span_type, args, kwargs):
        active = ActiveTrace(str(uuid.uuid4()), agent_name, streaming=self._streaming)
        token = _current_trace.set(active)
        root = SpanData(
            span_id=str(uuid.uuid4()),
            parent_id=None,
            name=agent_name,
            type=span_type,
            start_ms=_now_ms(),
            input=_str_truncate(args[0] if args else kwargs),
        )
        active.push_span(root)
        try:
            result = await fn(*args, **kwargs)
            root.output = _str_truncate(result)
            return result
        except Exception as exc:
            root.metadata["error"] = str(exc)
            raise
        finally:
            root.end_ms = _now_ms()
            active.pop_span(root)
            active.flush()
            _current_trace.reset(token)

    def span(self, name: str, span_type: str = "tool_call"):
        """Context manager for a manual child span."""
        active = _current_trace.get()
        if active is None:
            return _NoopSpanContext()
        s = SpanData(
            span_id=str(uuid.uuid4()),
            parent_id=active.current_span_id(),
            name=name,
            type=span_type,
            start_ms=_now_ms(),
        )
        return SpanContext(active, s)

    def log(self, message: str, **extra) -> None:
        """Add a timestamped note to the current active span.

        Convenience method that writes to the innermost span on the stack.
        No-ops silently when called outside a trace.

        Example::

            with agentlens.span("retrieve") as s:
                docs = retriever.invoke(query)
                agentlens.log("retrieved docs", count=len(docs))

        Args:
            message: Human-readable note (truncated to 1024 chars).
            **extra: Additional key/value metadata merged into the log entry.
        """
        active = _current_trace.get()
        if active is None:
            return
        # Find the innermost span currently on the stack
        span_id = active.current_span_id()
        if span_id is None:
            return
        for span in reversed(active.spans):
            if span.span_id == span_id:
                logs: list = span.metadata.setdefault("logs", [])
                entry: dict = {"ts_ms": _now_ms(), "message": str(message)[:1024]}
                entry.update({k: v for k, v in extra.items()})
                logs.append(entry)
                return

    def current_trace(self) -> Optional[ActiveTrace]:
        return _current_trace.get()
