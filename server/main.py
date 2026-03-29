"""FastAPI application entry point for AgentLens backend."""

import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from auth_deps import get_current_user
from auth_models import User
from models import SpanIn, SpansIn, TraceIn
from sse import bus
import storage
from storage import add_spans_to_trace, create_trace, get_trace, get_trace_pair, init_db, list_agents, list_traces
from diff import compute_diff
from otel_mapper import map_otlp_request
from alert_routes import router as alert_router
from alert_evaluator import evaluate_alert_rules
from auth_routes import router as auth_router
from auth_seed import seed_admin
from settings_routes import router as settings_router
from autopsy_routes import router as autopsy_router
from plugin_loader import load_plugins, notify_trace_created, notify_trace_completed
from prompt_routes import router as prompt_router
from eval_routes import router as eval_router
from replay_routes import router as replay_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_admin()
    load_plugins(app)
    yield


app = FastAPI(title="AgentLens", lifespan=lifespan)

# GZip compression for JSON responses (skip small payloads)
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(alert_router)
app.include_router(auth_router)
app.include_router(settings_router)
app.include_router(autopsy_router)
app.include_router(prompt_router)
app.include_router(eval_router)
app.include_router(replay_router)

_cors_origins_env = os.environ.get(
    "AGENTLENS_CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173",
)
_cors_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


# ── Health ────────────────────────────────────────────────────────────────────


@app.get("/api/health")
def health():
    """Health check with DB connectivity verification."""
    try:
        from sqlmodel import Session
        from sqlalchemy import text
        engine = storage._get_engine()
        with Session(engine) as session:
            session.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Health check DB error: %s", e)
        return {"status": "degraded", "db": "error"}


# ── Trace ingestion ───────────────────────────────────────────────────────────


@app.post("/api/traces", status_code=201)
def ingest_trace(body: TraceIn, user: User = Depends(get_current_user)):
    spans_data = [s.model_dump() for s in body.spans]
    trace = create_trace(body.trace_id, body.agent_name, spans_data, user_id=user.id)
    bus.publish("trace_created", {"trace_id": trace.id, "agent_name": trace.agent_name}, user_id=user.id)
    notify_trace_created(trace.id, trace.agent_name, trace.span_count)
    for s in body.spans:
        bus.publish("span_created", {"trace_id": trace.id, "span": s.model_dump()}, user_id=user.id)
    if trace.status == "completed":
        evaluate_alert_rules(trace.id, trace.agent_name)
        notify_trace_completed(trace.id, trace.agent_name)

    return {"trace_id": trace.id, "status": trace.status}


# ── Incremental span ingestion ────────────────────────────────────────────────


@app.post("/api/traces/{trace_id}/spans", status_code=201)
def ingest_spans(trace_id: str, body: SpansIn, user: User = Depends(get_current_user)):
    """Append spans to an existing trace and publish granular SSE events."""
    if len(body.spans) > 100:
        raise HTTPException(status_code=422, detail="Max 100 spans per request")

    spans_data = [s.model_dump() for s in body.spans]
    result = add_spans_to_trace(trace_id, spans_data, user_id=user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Trace not found")

    trace = result["trace"]
    new_spans = result["new_spans"]

    for s in body.spans:
        bus.publish("span_created", {"trace_id": trace_id, "span": s.model_dump()}, user_id=user.id)

    bus.publish("trace_updated", {
        "trace_id": trace.id,
        "status": trace.status,
        "span_count": trace.span_count,
        "total_cost_usd": trace.total_cost_usd,
        "duration_ms": trace.duration_ms,
    }, user_id=user.id)

    if trace.status == "completed":
        evaluate_alert_rules(trace.id, trace.agent_name)
        notify_trace_completed(trace.id, trace.agent_name)

    return {"trace_id": trace.id, "status": trace.status, "new_span_count": len(new_spans)}


# ── OTel OTLP HTTP ingestion ──────────────────────────────────────────────────


@app.post("/api/otel/v1/traces", status_code=200)
def ingest_otel_traces(body: dict, user: User = Depends(get_current_user)):
    """Receive OTLP HTTP JSON spans and store them as AgentLens traces."""
    groups = map_otlp_request(body)
    if not groups:
        return {"status": "ok", "traces_received": 0}

    for trace_id, agent_name, spans_data in groups:
        existing = get_trace(trace_id, user_id=user.id)
        if existing:
            result = add_spans_to_trace(trace_id, spans_data, user_id=user.id)
            if result:
                trace = result["trace"]
                bus.publish("trace_updated", {
                    "trace_id": trace.id,
                    "status": trace.status,
                    "span_count": trace.span_count,
                    "total_cost_usd": trace.total_cost_usd,
                    "duration_ms": trace.duration_ms,
                }, user_id=user.id)
        else:
            trace = create_trace(trace_id, agent_name, spans_data, user_id=user.id)
            bus.publish("trace_created", {"trace_id": trace.id, "agent_name": trace.agent_name}, user_id=user.id)
            notify_trace_created(trace.id, trace.agent_name, trace.span_count)

        for s in spans_data:
            bus.publish("span_created", {"trace_id": trace_id, "span": s}, user_id=user.id)

        if trace.status == "completed":
            evaluate_alert_rules(trace.id, trace.agent_name)
            notify_trace_completed(trace.id, trace.agent_name)

    return {"status": "ok", "traces_received": len(groups)}


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
    user: User = Depends(get_current_user),
):
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
        user_id=user.id,
    )
    return {"traces": traces, "total": total, "limit": limit, "offset": offset}


# ── Agent names ────────────────────────────────────────────────────────────────


@app.get("/api/agents")
def list_agents_endpoint(user: User = Depends(get_current_user)):
    """Return distinct agent names for filter dropdowns."""
    return {"agents": list_agents(user_id=user.id)}


# ── Trace comparison — MUST be registered before /{trace_id} ─────────────────


@app.get("/api/traces/compare")
def compare_traces_endpoint(
    left: str = Query(..., description="Left trace ID"),
    right: str = Query(..., description="Right trace ID"),
    user: User = Depends(get_current_user),
):
    """Return both traces + spans + structural diff metadata."""
    pair = get_trace_pair(left, right, user_id=user.id)
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
async def stream_traces(user: User = Depends(get_current_user)):
    async def event_generator():
        async for chunk in bus.subscribe(user_id=user.id):
            yield chunk

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Single trace detail ───────────────────────────────────────────────────────


@app.get("/api/traces/{trace_id}")
def get_trace_endpoint(trace_id: str, user: User = Depends(get_current_user)):
    result = get_trace(trace_id, user_id=user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Trace not found")
    return result


# ── Static SPA — MUST be mounted last ────────────────────────────────────────

_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
