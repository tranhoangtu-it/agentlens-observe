"""SQLModel table and Pydantic schemas for AI-powered failure autopsy."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Index
from sqlmodel import SQLModel, Field


class AutopsyResult(SQLModel, table=True):
    __tablename__ = "autopsy_result"
    id: str = Field(primary_key=True)
    trace_id: str = Field(index=True)
    user_id: str = Field(index=True)
    root_cause: str
    summary: str
    severity: str = "info"  # "critical" | "warning" | "info"
    suggested_fix: str
    affected_span_ids_json: str = "[]"  # JSON array of span IDs
    llm_provider: str
    llm_model: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_autopsy_trace_user", "trace_id", "user_id"),
    )


class AutopsyRequestIn(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None


class AutopsyOut(BaseModel):
    id: str
    trace_id: str
    root_cause: str
    summary: str
    severity: str
    suggested_fix: str
    affected_span_ids: list[str]
    llm_provider: str
    llm_model: str
    created_at: str
    cached: bool = False
