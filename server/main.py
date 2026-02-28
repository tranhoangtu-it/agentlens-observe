"""FastAPI application entry point for AgentLens backend."""

import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from models import SpanIn, SpansIn, TraceIn
from sse import bus
from storage import add_spans_to_trace, create_trace, get_trace, get_trace_pair, init_db, list_agents, list_traces
from diff import compute_diff


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="AgentLens", lifespan=lifespan)

# GZip compression for JSON responses (skip small payloads)
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────────────────────


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ── Trace ingestion ───────────────────────────────────────────────────────────


@app.post("/api/traces", status_code=201)
def ingest_trace(body: TraceIn):
    spans_data = [s.model_dump() for s in body.spans]
    trace = create_trace(body.trace_id, body.agent_name, spans_data)
    bus.publish("trace_created", {"trace_id": trace.id, "agent_name": trace.agent_name})
    # Publish span_created for each span so live detail pages update
    for s in body.spans:
        bus.publish("span_created", {"trace_id": trace.id, "span": s.model_dump()})
    return {"trace_id": trace.id, "status": trace.status}


# ── Incremental span ingestion ────────────────────────────────────────────────


@app.post("/api/traces/{trace_id}/spans", status_code=201)
def ingest_spans(trace_id: str, body: SpansIn):
    """Append spans to an existing trace and publish granular SSE events."""
    if len(body.spans) > 100:
        raise HTTPException(status_code=422, detail="Max 100 spans per request")

    spans_data = [s.model_dump() for s in body.spans]
    result = add_spans_to_trace(trace_id, spans_data)
    if result is None:
        raise HTTPException(status_code=404, detail="Trace not found")

    trace = result["trace"]
    new_spans = result["new_spans"]

    # Publish per-span event
    for s in body.spans:
        bus.publish("span_created", {"trace_id": trace_id, "span": s.model_dump()})

    # Publish aggregate update
    bus.publish("trace_updated", {
        "trace_id": trace.id,
        "status": trace.status,
        "span_count": trace.span_count,
        "total_cost_usd": trace.total_cost_usd,
        "duration_ms": trace.duration_ms,
    })

    return {"trace_id": trace.id, "status": trace.status, "new_span_count": len(new_spans)}


# ── Trace listing ─────────────────────────────────────────────────────────────


@app.get("/api/traces")
def list_traces_endpoint(
    q: Optional[str] = Query(None, description="LIKE search on agent_name"),
    status: Optional[str] = Query(None, description="Filter by status: completed/running/error"),
    agent_name: Optional[str] = Query(None, description="Exact agent_name match"),
    from_date: Optional[str] = Query(None, description="ISO date lower bound on created_at"),
    to_date: Optional[str] = Query(None, description="ISO date upper bound on created_at"),
    min_cost: Optional[float] = Query(None, ge=0),
    max_cost: Optional[float] = Query(None, ge=0),
    sort: str = Query("created_at"),
    order: str = Query("desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    # Validate date strings early to return 422 with clear message
    for date_str, param in [(from_date, "from_date"), (to_date, "to_date")]:
        if date_str is not None:
            try:
                from datetime import datetime as _dt
                _dt.fromisoformat(date_str)
            except ValueError:
                raise HTTPException(status_code=422, detail=f"Invalid date format for {param}: {date_str!r}")

    traces, total = list_traces(
        q=q,
        status=status,
        agent_name=agent_name,
        from_date=from_date,
        to_date=to_date,
        min_cost=min_cost,
        max_cost=max_cost,
        sort=sort,
        order=order,
        limit=limit,
        offset=offset,
    )
    return {"traces": traces, "total": total, "limit": limit, "offset": offset}


# ── Agent names ────────────────────────────────────────────────────────────────


@app.get("/api/agents")
def list_agents_endpoint():
    """Return distinct agent names for filter dropdowns."""
    return {"agents": list_agents()}


# ── Trace comparison — MUST be registered before /{trace_id} ─────────────────


@app.get("/api/traces/compare")
def compare_traces_endpoint(
    left: str = Query(..., description="Left trace ID"),
    right: str = Query(..., description="Right trace ID"),
):
    """Return both traces + spans + structural diff metadata."""
    pair = get_trace_pair(left, right)
    if not pair:
        raise HTTPException(status_code=404, detail="One or both traces not found")

    # Convert SQLModel Span objects to plain dicts for the diff algorithm
    def span_to_dict(s) -> dict:
        return {
            "id": s.id,
            "parent_id": s.parent_id,
            "name": s.name,
            "type": s.type,
            "start_ms": s.start_ms,
            "end_ms": s.end_ms,
            "input": s.input,
            "output": s.output,
            "cost_usd": s.cost_usd,
            "cost_input_tokens": s.cost_input_tokens,
            "cost_output_tokens": s.cost_output_tokens,
        }

    left_spans_dicts = [span_to_dict(s) for s in pair["left"]["spans"]]
    right_spans_dicts = [span_to_dict(s) for s in pair["right"]["spans"]]
    diff = compute_diff(left_spans_dicts, right_spans_dicts)

    return {
        "left": pair["left"],
        "right": pair["right"],
        "diff": diff,
    }


# ── SSE stream — MUST be registered before /{trace_id} ───────────────────────


@app.get("/api/traces/stream")
async def stream_traces():
    async def event_generator():
        async for chunk in bus.subscribe():
            yield chunk

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Single trace detail ───────────────────────────────────────────────────────


@app.get("/api/traces/{trace_id}")
def get_trace_endpoint(trace_id: str):
    result = get_trace(trace_id)
    if not result:
        raise HTTPException(status_code=404, detail="Trace not found")
    return result


# ── Static SPA — MUST be mounted last ────────────────────────────────────────

_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
