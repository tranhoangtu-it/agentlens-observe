"""SQLite CRUD layer for AgentLens using SQLModel + WAL mode."""

import json
import os
from typing import Optional

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine, select

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


def list_traces(agent_name: Optional[str] = None, limit: int = 50, offset: int = 0) -> list[Trace]:
    """Return paginated traces, newest first."""
    engine = _get_engine()
    with Session(engine) as session:
        stmt = select(Trace)
        if agent_name:
            stmt = stmt.where(Trace.agent_name == agent_name)
        stmt = stmt.order_by(Trace.created_at.desc()).offset(offset).limit(limit)
        return session.exec(stmt).all()


def get_trace(trace_id: str) -> Optional[dict]:
    """Return trace with its spans, or None if not found."""
    engine = _get_engine()
    with Session(engine) as session:
        trace = session.get(Trace, trace_id)
        if not trace:
            return None
        spans = session.exec(select(Span).where(Span.trace_id == trace_id)).all()
        return {"trace": trace, "spans": spans}
