# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is AgentLens

Self-hosted observability platform for debugging AI agents. Traces tool calls, inspects decision trees, monitors agent behavior. Open-source alternative to LangSmith/Langfuse.

## Architecture

Monorepo with 4 independent packages:

- **server/** — FastAPI backend (Python 3.11+), SQLite default / PostgreSQL via `DATABASE_URL`. Uses SQLModel ORM, JWT auth, SSE for real-time updates. Serves built dashboard as static files in production.
- **dashboard/** — React 19 + TypeScript SPA. Vite build, Tailwind CSS, React Flow (`@xyflow/react`) for trace topology graphs, Recharts for cost charts.
- **sdk/** — Python SDK (`agentlens-observe` on PyPI, v0.6.0). Framework integrations: LangChain, CrewAI, AutoGen, LlamaIndex, Google ADK, OpenTelemetry.
- **sdk-ts/** — TypeScript SDK (`agentlens-observe` on npm, v0.6.0). Built with tsup, dual CJS/ESM.

Data flow: SDK → `POST /api/traces` or `/api/traces/{id}/spans` → SQLModel storage → SSE bus → Dashboard. Also accepts OTLP HTTP at `/api/otel/v1/traces`.

## Common Commands

### Server
```bash
cd server
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Tests
pytest                          # all tests
pytest tests/test_storage.py    # single file
pytest -k test_create_trace     # single test
```

### Dashboard
```bash
cd dashboard
npm install
npm run dev         # dev server (Vite, port 5173)
npm run build       # production build
npm run lint        # ESLint
```

### Python SDK
```bash
cd sdk
pip install -e ".[dev]"         # editable install with test deps
pytest                          # run tests
pytest tests/test_tracer.py     # single file
```

### TypeScript SDK
```bash
cd sdk-ts
npm install
npm run build       # tsup build
npm run test        # vitest
npm run typecheck   # tsc --noEmit
```

### Docker (full stack)
```bash
docker compose up               # dashboard at localhost:3000
```

## Key Design Decisions

- **Tenant isolation**: All queries filter by `user_id` from JWT. The `User` dependency is injected via `get_current_user` (auth_deps.py).
- **SSE bus** (sse.py): In-memory pub/sub for real-time trace/span events, scoped per user.
- **Incremental ingestion**: Traces can be created empty then filled via `POST /api/traces/{id}/spans` (max 100 spans/request).
- **Alert system**: Rule-based alerts (alert_models/evaluator/notifier/routes/storage) that evaluate when a trace completes.
- **OTel bridge**: `otel_mapper.py` converts OTLP HTTP JSON to internal trace format.
- **Trace comparison**: `diff.py` computes structural diffs between two traces' span trees.
- **Cost tracking**: Both SDKs compute token costs per model (sdk: `cost.py`, sdk-ts: `cost.ts`).
- **SDK integrations** are in `sdk/agentlens/integrations/` — each file wraps a specific framework (langchain, crewai, autogen, llamaindex, google_adk).

## Environment Variables

- `AGENTLENS_DB_PATH` — SQLite file path (default: `./agentlens.db`)
- `DATABASE_URL` — PostgreSQL connection string (overrides SQLite)
- `AGENTLENS_CORS_ORIGINS` — Comma-separated allowed origins (default: `localhost:3000,localhost:5173`)
- `AGENTLENS_JWT_SECRET` — JWT signing secret
