"""SQLite CRUD layer for AgentLens using SQLModel + WAL mode."""

import json
import os
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import func, text
from sqlmodel import Session, SQLModel, col, create_engine, select

from models import Span, Trace

DB_PATH = os.environ.get("AGENTLENS_DB_PATH", "./agentlens.db")
_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
    return _engine


def init_db():
    """Create tables and enable WAL mode for better concurrency."""
    engine = _get_engine()
    SQLModel.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.commit()


def create_trace(trace_id: str, agent_name: str, spans_data: list[dict]) -> Trace:
    """Insert trace + spans, compute and store aggregates."""
    engine = _get_engine()

    spans = []
    for s in spans_data:
        cost = s.get("cost") or {}
        meta = s.get("metadata")
        spans.append(Span(
            id=s["span_id"],
            trace_id=trace_id,
            parent_id=s.get("parent_id"),
            name=s["name"],
            type=s["type"],
            start_ms=s["start_ms"],
            end_ms=s.get("end_ms"),
            input=s.get("input"),
            output=s.get("output"),
            cost_model=cost.get("model"),
            cost_input_tokens=cost.get("input_tokens"),
            cost_output_tokens=cost.get("output_tokens"),
            cost_usd=cost.get("usd"),
            metadata_json=json.dumps(meta) if meta else None,
        ))

    # Aggregate totals
    total_cost = sum(sp.cost_usd or 0.0 for sp in spans) or None
    total_tokens = sum((sp.cost_input_tokens or 0) + (sp.cost_output_tokens or 0) for sp in spans) or None

    start_times = [sp.start_ms for sp in spans if sp.start_ms]
    end_times = [sp.end_ms for sp in spans if sp.end_ms]
    duration_ms = (max(end_times) - min(start_times)) if start_times and end_times else None

    # Determine status: completed if all spans have end_ms
    status = "completed" if spans and all(sp.end_ms is not None for sp in spans) else "running"

    trace = Trace(
        id=trace_id,
        agent_name=agent_name,
        total_cost_usd=total_cost,
        total_tokens=total_tokens,
        span_count=len(spans),
        duration_ms=duration_ms,
        status=status,
    )

    with Session(engine) as session:
        # Upsert: delete existing spans/trace then re-insert
        existing = session.get(Trace, trace_id)
        if existing:
            session.execute(text("DELETE FROM span WHERE trace_id = :tid"), {"tid": trace_id})
            session.delete(existing)
            session.flush()

        session.add(trace)
        for sp in spans:
            session.add(sp)
        session.commit()
        session.refresh(trace)

    return trace


def list_traces(
    q: Optional[str] = None,
    status: Optional[str] = None,
    agent_name: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    min_cost: Optional[float] = None,
    max_cost: Optional[float] = None,
    sort: str = "created_at",
    order: str = "desc",
    limit: int = 50,
    offset: int = 0,
) -> Tuple[list[Trace], int]:
    """Return paginated traces with optional filters. Returns (traces, total)."""
    # Allowed sort columns to prevent injection
    _SORT_COLS = {"created_at", "total_cost_usd", "duration_ms", "span_count", "agent_name", "status"}
    if sort not in _SORT_COLS:
        sort = "created_at"
    if order not in ("asc", "desc"):
        order = "desc"

    engine = _get_engine()
    with Session(engine) as session:
        stmt = select(Trace)
        count_stmt = select(func.count()).select_from(Trace)

        # Build WHERE clauses
        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(col(Trace.agent_name).like(pattern))
            count_stmt = count_stmt.where(col(Trace.agent_name).like(pattern))
        if agent_name:
            stmt = stmt.where(Trace.agent_name == agent_name)
            count_stmt = count_stmt.where(Trace.agent_name == agent_name)
        if status:
            stmt = stmt.where(Trace.status == status)
            count_stmt = count_stmt.where(Trace.status == status)
        if from_date:
            dt = datetime.fromisoformat(from_date).replace(tzinfo=timezone.utc)
            stmt = stmt.where(Trace.created_at >= dt)
            count_stmt = count_stmt.where(Trace.created_at >= dt)
        if to_date:
            dt = datetime.fromisoformat(to_date).replace(tzinfo=timezone.utc)
            stmt = stmt.where(Trace.created_at <= dt)
            count_stmt = count_stmt.where(Trace.created_at <= dt)
        if min_cost is not None:
            stmt = stmt.where(Trace.total_cost_usd >= min_cost)
            count_stmt = count_stmt.where(Trace.total_cost_usd >= min_cost)
        if max_cost is not None:
            stmt = stmt.where(Trace.total_cost_usd <= max_cost)
            count_stmt = count_stmt.where(Trace.total_cost_usd <= max_cost)

        # Sort
        sort_col = getattr(Trace, sort)
        if order == "desc":
            stmt = stmt.order_by(sort_col.desc())
        else:
            stmt = stmt.order_by(sort_col.asc())

        total = session.exec(count_stmt).one()
        traces = session.exec(stmt.offset(offset).limit(limit)).all()
        return list(traces), total


def list_agents() -> list[str]:
    """Return sorted list of distinct agent names."""
    engine = _get_engine()
    with Session(engine) as session:
        rows = session.exec(select(Trace.agent_name).distinct()).all()
        return sorted(set(r for r in rows if r))


def get_trace(trace_id: str) -> Optional[dict]:
    """Return trace with its spans, or None if not found."""
    engine = _get_engine()
    with Session(engine) as session:
        trace = session.get(Trace, trace_id)
        if not trace:
            return None
        spans = session.exec(select(Span).where(Span.trace_id == trace_id)).all()
        return {"trace": trace, "spans": spans}


def get_trace_pair(left_id: str, right_id: str) -> Optional[dict]:
    """Fetch two traces + their spans for comparison. Returns None if either trace missing."""
    engine = _get_engine()
    with Session(engine) as session:
        left_trace = session.get(Trace, left_id)
        right_trace = session.get(Trace, right_id)
        if not left_trace or not right_trace:
            return None
        left_spans = list(session.exec(select(Span).where(Span.trace_id == left_id)).all())
        right_spans = list(session.exec(select(Span).where(Span.trace_id == right_id)).all())
        return {
            "left": {"trace": left_trace, "spans": left_spans},
            "right": {"trace": right_trace, "spans": right_spans},
        }


def add_spans_to_trace(trace_id: str, spans_data: list[dict]) -> Optional[dict]:
    """Append spans to existing trace, recompute aggregates. Returns {trace, new_spans} or None."""
    engine = _get_engine()

    with Session(engine) as session:
        trace = session.get(Trace, trace_id)
        if not trace:
            return None

        new_spans = []
        for s in spans_data:
            cost = s.get("cost") or {}
            meta = s.get("metadata")
            span = Span(
                id=s["span_id"],
                trace_id=trace_id,
                parent_id=s.get("parent_id"),
                name=s["name"],
                type=s["type"],
                start_ms=s["start_ms"],
                end_ms=s.get("end_ms"),
                input=s.get("input"),
                output=s.get("output"),
                cost_model=cost.get("model"),
                cost_input_tokens=cost.get("input_tokens"),
                cost_output_tokens=cost.get("output_tokens"),
                cost_usd=cost.get("usd"),
                metadata_json=json.dumps(meta) if meta else None,
            )
            # Upsert: skip if span_id already exists
            existing_span = session.get(Span, span.id)
            if existing_span is None:
                session.add(span)
                new_spans.append(span)

        # Recompute aggregates from all spans in trace
        all_spans = session.exec(select(Span).where(Span.trace_id == trace_id)).all()
        all_spans = list(all_spans) + new_spans

        total_cost = sum(sp.cost_usd or 0.0 for sp in all_spans) or None
        total_tokens = sum(
            (sp.cost_input_tokens or 0) + (sp.cost_output_tokens or 0) for sp in all_spans
        ) or None

        start_times = [sp.start_ms for sp in all_spans if sp.start_ms]
        end_times = [sp.end_ms for sp in all_spans if sp.end_ms]
        duration_ms = (max(end_times) - min(start_times)) if start_times and end_times else None

        # completed only when all spans have end_ms
        status = "completed" if all_spans and all(sp.end_ms is not None for sp in all_spans) else "running"

        trace.total_cost_usd = total_cost
        trace.total_tokens = total_tokens
        trace.span_count = len(all_spans)
        trace.duration_ms = duration_ms
        trace.status = status

        session.add(trace)
        session.commit()
        session.refresh(trace)

        return {"trace": trace, "new_spans": new_spans}
