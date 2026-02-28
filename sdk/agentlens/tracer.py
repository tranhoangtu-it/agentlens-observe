"""Core tracing logic: Tracer, SpanData, context management."""
import functools
import inspect
import logging
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .transport import post_trace

logger = logging.getLogger("agentlens")

_current_trace: ContextVar[Optional["ActiveTrace"]] = ContextVar(
    "_current_trace", default=None
)


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
    def __init__(self, trace_id: str, agent_name: str):
        self.trace_id = trace_id
        self.agent_name = agent_name
        self.spans: list[SpanData] = []
        self._span_stack: list[str] = []  # stack of span_ids

    def current_span_id(self) -> Optional[str]:
        return self._span_stack[-1] if self._span_stack else None

    def push_span(self, span: SpanData):
        self.spans.append(span)
        self._span_stack.append(span.span_id)

    def pop_span(self):
        if self._span_stack:
            self._span_stack.pop()

    def flush(self):
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

    def __enter__(self):
        self._active.push_span(self._span)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._span.end_ms = _now_ms()
        self._active.pop_span()
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
    def __enter__(self): return self
    def __exit__(self, *a): return False


class Tracer:
    """Main SDK entry point. One instance shared globally."""

    def __init__(self):
        self._server_url: Optional[str] = None

    def configure(self, server_url: str):
        self._server_url = server_url

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
        active = ActiveTrace(str(uuid.uuid4()), agent_name)
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
            active.pop_span()
            active.flush()
            _current_trace.reset(token)

    async def _run_async(self, fn, agent_name, span_type, args, kwargs):
        active = ActiveTrace(str(uuid.uuid4()), agent_name)
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
            active.pop_span()
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

    def current_trace(self) -> Optional[ActiveTrace]:
        return _current_trace.get()
