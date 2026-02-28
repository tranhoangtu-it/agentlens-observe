"""SQLModel table definitions and Pydantic request schemas for AgentLens."""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import Index
from sqlmodel import SQLModel, Field


# ── Database tables ──────────────────────────────────────────────────────────


class Trace(SQLModel, table=True):
    id: str = Field(primary_key=True)
    agent_name: str = Field(index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True,
    )
    total_cost_usd: Optional[float] = None
    total_tokens: Optional[int] = None
    span_count: int = 0
    duration_ms: Optional[int] = None
    status: str = Field(default="running", index=True)

    __table_args__ = (
        Index("ix_trace_status_created", "status", "created_at"),
        Index("ix_trace_agent_created", "agent_name", "created_at"),
        Index("ix_trace_cost", "total_cost_usd"),
    )


class Span(SQLModel, table=True):
    id: str = Field(primary_key=True)
    trace_id: str = Field(index=True)
    parent_id: Optional[str] = None
    name: str
    type: str
    start_ms: int
    end_ms: Optional[int] = None
    input: Optional[str] = None
    output: Optional[str] = None
    cost_model: Optional[str] = None
    cost_input_tokens: Optional[int] = None
    cost_output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    metadata_json: Optional[str] = None


# ── Request schemas ───────────────────────────────────────────────────────────


class CostIn(BaseModel):
    model: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    usd: Optional[float] = None


class SpanIn(BaseModel):
    span_id: str
    parent_id: Optional[str] = None
    name: str
    type: str
    start_ms: int
    end_ms: Optional[int] = None
    input: Optional[str] = None
    output: Optional[str] = None
    cost: Optional[CostIn] = None
    metadata: Optional[dict] = None


class TraceIn(BaseModel):
    trace_id: str
    agent_name: str
    spans: list[SpanIn]


class SpansIn(BaseModel):
    """Body for POST /api/traces/{trace_id}/spans — incremental span ingestion."""
    spans: list[SpanIn]
