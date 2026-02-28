# AgentLens v0.2.0 — Codebase Summary

**Total Files:** 104 | **Total Tokens:** 410K | **Languages:** Python, TypeScript, JavaScript, HTML, CSS

## Quick Stats

| Metric | Value |
|--------|-------|
| **Dashboard Size** | 282KB (index chunk) |
| **Recharts Bundle** | 335KB |
| **React Flow Bundle** | 232KB |
| **Compare Page Bundle** | 14KB (lazy) |
| **Server Tests** | 38 tests |
| **SDK Tests** | 52 tests |
| **Coverage** | >82% |
| **Python Version** | 3.10+ (SDK), 3.11+ (Server) |
| **Node Version** | 18+ |

## File-by-File Breakdown

### Dashboard (`dashboard/src/`, ~3,500 LOC)

#### Pages (3 files, ~800 LOC)
- **`pages/traces-list-page.tsx`** — List all traces with search, filters, pagination. Uses trace-list-table component. Event listeners for trace_created updates.
- **`pages/trace-detail-page.tsx`** — Single trace with topology graph + span detail panel. Real-time updates via useSSETraces. Pulse animation on running nodes.
- **`pages/trace-compare-page.tsx`** — Side-by-side topology comparison. Lazy-loaded (14KB chunk). Diff algorithm from backend. Color-coded matching.

#### Components (11 files, ~2,000 LOC)
- **`trace-list-table.tsx`** — Virtualized table (@tanstack/react-virtual). Sortable columns. Pagination controls. React.memo for performance.
- **`trace-topology-graph.tsx`** — React Flow DAG. Nodes: spans. Edges: parent-child. Pulse animation on running. Color by status.
- **`trace-compare-graphs.tsx`** — Dual React Flow instances. Side-by-side comparison. Matching spans highlighted. Insertions (blue), deletions (red).
- **`span-detail-panel.tsx`** — Detailed span view. Input (JSON), output (JSON), cost breakdown, duration, metadata, logs.
- **`span-diff-panel.tsx`** — LCS-matched span diff. Line-by-line color coding. Regex highlight changes.
- **`cost-summary-chart.tsx`** — Recharts pie chart. Cost by model. Legend. Hover tooltip with exact USD.
- **`trace-search-bar.tsx`** — Full-text search input. Debounced (300ms). Updates query param `q`.
- **`trace-filter-controls.tsx`** — Dropdown filters: status (running|completed|error), agent_name, date range picker, cost range slider.
- **`pagination-controls.tsx`** — Page controls: limit selector (10, 25, 50, 100), prev/next buttons, current page indicator.
- **UI Primitives** (9 files, ~600 LOC) — shadcn/ui base components: badge, button, card, input, skeleton, table, separator, tooltip, scroll-area.

#### Hooks & Utilities (5 files, ~700 LOC)
- **`use-sse-traces.ts`** — EventSource subscription. Listens to span_created + trace_updated. Updates local state.
- **`use-live-trace-detail.ts`** — Real-time trace fetching + SSE. Merges API response with stream updates.
- **`use-trace-filters.ts`** — Filter state management (q, status, agent_name, date, cost, sort, order, limit, offset). Updates URL params.
- **`api-client.ts`** — Typed fetch wrapper. Methods: listTraces(), getTrace(), compareTaces(), listAgents(). Error handling + retry logic.
- **`diff-utils.ts`** — LCS matching, color assignment (green/red/blue). Span similarity scoring by name + type + duration.

#### Styling
- **`index.css`** — Tailwind setup. CSS variables for dark theme (--slate-*, --blue-*, --red-*, --green-*). Pulse animation on `.animate-pulse`.

#### Config (5 files)
- **`vite.config.ts`** — Build config. Code splitting strategy. React plugin. URL base `/`.
- **`tailwind.config.js`** — Content paths, theme extensions, plugins (forms, animations).
- **`tsconfig.json`** — Strict mode, React JSX. Path alias `@/*` → `src/`.
- **`package.json`** — Dependencies: React 19, Vite 7, React Flow 12, Tailwind 3, Recharts 3, @tanstack/react-virtual, Radix UI, etc.
- **`index.html`** — Root HTML. Mounts app to `#root`.

### Server (`server/`, ~600 LOC)

#### Core Endpoints (1 file, ~200 LOC)
- **`main.py`** — FastAPI app entry. Routes:
  - `POST /api/traces` — Create trace
  - `POST /api/traces/{id}/spans` — Incremental span ingestion
  - `GET /api/traces` — List traces (q, status, agent, date, cost, sort, order, limit, offset)
  - `GET /api/traces/{id}` — Fetch single trace
  - `GET /api/traces/compare` — Compute diff
  - `GET /api/agents` — List agent names
  - `GET /api/health` — Liveness check
  - Middleware: GZip (>1KB), CORS (all origins)

#### Database Models (1 file, ~80 LOC)
- **`models.py`** — SQLModel + Pydantic:
  - `Trace` table: id, agent_name, created_at, status, span_count, total_cost_usd, total_tokens, duration_ms
  - Compound indexes: (status, created_at), (agent_name, created_at), (total_cost_usd)
  - `Span` table: id, trace_id, parent_id, name, type, start_ms, end_ms, input, output, cost_*, metadata_json
  - Request schemas: `TraceIn`, `SpanIn`, `SpansIn`, `CostIn`

#### Storage & CRUD (1 file, ~200 LOC)
- **`storage.py`** — SQLite interface:
  - `init_db()` — Create tables + indexes
  - `create_trace()` — Insert trace + spans
  - `add_spans_to_trace()` — Append spans to existing trace
  - `get_trace()` — Fetch by ID (with all spans)
  - `list_traces()` — Query with filters, sorting, pagination
  - `list_agents()` — Distinct agent names
  - Filtering: full-text (q), status, agent_name, date range, cost range

#### SSE Bus (1 file, ~60 LOC)
- **`sse.py`** — In-memory event bus:
  - `publish(event_name, data)` — Broadcast to all subscribers
  - Events: `span_created`, `trace_updated`
  - Subscribers: List of EventSource connections

#### Diff Algorithm (1 file, ~100 LOC)
- **`diff.py`** — LCS span tree comparison:
  - `compute_diff(left, right)` — Match spans by LCS
  - Similarity scoring: name, type, duration
  - Color assignment: green (match), red (deletion), blue (insertion)
  - Returns: matches, insertions, deletions

#### Tests (3 files, ~38 tests, ~400 LOC)
- **`test_api_endpoints.py`** — Endpoint tests: POST /traces, POST /spans, GET /traces (filters), GET /compare
- **`test_sse.py`** — Event bus: publish, subscribe, multiple subscribers
- **`test_storage.py`** — CRUD: create, list, filter, sort, pagination
- **`conftest.py`** — Fixtures: test client, in-memory DB

#### Config
- **`requirements.txt`** — Dependencies: fastapi, uvicorn, sqlmodel, sqlalchemy, pydantic
- **`Dockerfile`** — Multi-stage: node:20 (build React) + python:3.11 (runtime)

### SDK (`sdk/`, ~800 LOC)

#### Public API (1 file, ~20 LOC)
- **`__init__.py`** — Exports: `Tracer`, `SpanExporter`, version 0.2.0

#### Tracer (1 file, ~200 LOC)
- **`tracer.py`** — Core SDK logic:
  - `Tracer.trace()` — Decorator for agent functions. Captures span hierarchy.
  - `Tracer.span()` — Context manager for child spans (parent-child links).
  - `Tracer.log()` — Add metadata logs to current span.
  - `Tracer.configure()` — Set server_url, batch_size, batch_interval.
  - `Tracer.add_exporter()` — Attach OTel or custom exporters.
  - `SpanExporter` protocol — Interface for exporters.

#### Transport (1 file, ~150 LOC)
- **`transport.py`** — HTTP batch queue:
  - `HTTPTransport` — httpx-based client
  - Batch queue: configurable batch_size (default 50), batch_interval (default 5s)
  - `flush()` — Send pending traces
  - Auto-flush on timer or queue full
  - Fire-and-forget (non-blocking)
  - Retry logic on 5xx errors

#### Pricing (1 file, ~150 LOC)
- **`cost.py`** — LLM pricing table:
  - 27 models: GPT-4.1, Claude 4, Gemini 2.0, DeepSeek, Llama 3.3, Mixtral, PaLM 2, etc.
  - Per-token costs (input, output)
  - `calculate_cost(model, input_tokens, output_tokens) -> float`

#### Integrations (5 files, ~150 LOC)
- **`integrations/langchain.py`** — LangChain callback handler. Auto-capture tool calls, LLM invocations.
- **`integrations/crewai.py`** — CrewAI patch. Instruments all Crew.execute() calls.
- **`integrations/autogen.py`** — AutoGen patch. Wraps ConversableAgent.generate_reply().
- **`integrations/llamaindex.py`** — LlamaIndex callback. Integrates with CallbackManager.
- **`integrations/google_adk.py`** — Google ADK patch. Instruments Agent.run() + tool invocations.

#### Exporters (1 file, ~80 LOC)
- **`exporters/otel.py`** — OpenTelemetry exporter. Converts AgentLens spans → OTel trace format. Sends to OTel collector.

#### Tests (3 files, ~52 tests, ~400 LOC)
- **`test_tracer.py`** — Tracer decorator, span context, parent-child hierarchy, logging
- **`test_transport.py`** — Batch queue, flush, retry logic, concurrent requests
- **`test_cost.py`** — Pricing calculations for all 27 models
- **`conftest.py`** — Fixtures: mock server, test traces

#### Config
- **`pyproject.toml`** — Package metadata, dependencies (httpx, pytest, respx), entry point
- **`README.md`** — SDK usage guide, framework examples, API reference

### Utilities & Config

#### Root
- **`Dockerfile`** — Multi-stage: node build + python runtime
- **`docker-compose.yml`** — Local dev: server (port 8000), dashboard (port 5173)
- **`README.md`** — Project overview, quickstart, features, tech stack

#### Scripts
- **`scripts/seed-demo-data.py`** — Generate sample traces for demo
- **`scripts/capture-demo-screenshots.js`** — Screenshot automation

## Dependency Graph

```
dashboard/
├── React 19
├── Vite 7
├── TypeScript 5
├── Tailwind CSS 3
├── Radix UI (primitives)
├── React Flow 12 (topologies)
├── Recharts 3 (cost chart)
├── @tanstack/react-virtual (table virtualization)
└── axios (API calls)

server/
├── FastAPI 0.100+
├── Uvicorn (ASGI)
├── SQLModel (ORM)
├── SQLAlchemy 2.0
├── Pydantic 2.0 (validation)
└── pytest (testing)

sdk/
├── httpx (HTTP client)
├── Pydantic (validation)
└── For testing: pytest, respx (HTTP mocking)
```

## Test Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| `server/storage.py` | 12 | 95% |
| `server/main.py` | 16 | 88% |
| `server/diff.py` | 10 | 90% |
| `sdk/tracer.py` | 18 | 92% |
| `sdk/transport.py` | 20 | 85% |
| `sdk/cost.py` | 14 | 100% |
| **Total** | **90** | **>82%** |

## Build & Deployment

### Development Build
```bash
cd dashboard && npm run dev      # React dev server (Vite, :5173)
cd server && uvicorn main:app --reload --port 8000
cd sdk && pip install -e ".[dev]"
```

### Production Build
```dockerfile
# Multi-stage
# Stage 1: React build (node:20-alpine)
# Stage 2: Python runtime (python:3.11-slim)
# Result: Single Docker image, React served from /static

docker run -p 3000:3000 tranhoangtu/agentlens:0.2.0
```

### PyPI Distribution
```bash
cd sdk
pip install agentlens-observe==0.2.0
```

## Known Limitations & Future Work

### Current (v0.2.0)
- SQLite backend (good for single-machine, limited concurrency)
- No auth/RBAC (private network assumed)
- No alert system
- No time-travel debugging (replay)

### Roadmap
- PostgreSQL backend
- OTel ingestion (receive spans from other systems)
- TypeScript SDK
- Alerting framework
- Multi-tenant auth
- Replay/time-travel debugging
