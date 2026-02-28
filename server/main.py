"""FastAPI application entry point for AgentLens backend."""

import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from models import TraceIn
from sse import bus
from storage import create_trace, get_trace, init_db, list_traces


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="AgentLens", lifespan=lifespan)

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
    return {"trace_id": trace.id, "status": trace.status}


# ── Trace listing ─────────────────────────────────────────────────────────────


@app.get("/api/traces")
def list_traces_endpoint(
    agent_name: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    traces = list_traces(agent_name=agent_name, limit=limit, offset=offset)
    return {"traces": traces, "count": len(traces)}


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
