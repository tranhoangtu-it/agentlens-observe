# AgentLens v0.6.0 — Codebase Summary

**Languages:** Python, TypeScript, JavaScript, HTML, CSS

## Quick Stats

| Metric | Value |
|--------|-------|
| **Dashboard Size** | 282KB (index chunk) |
| **Recharts Bundle** | 335KB |
| **React Flow Bundle** | 232KB |
| **Compare Page Bundle** | 14KB (lazy) |
| **Server Tests** | 86 tests |
| **SDK Tests** | 52 tests (Python) + 30 tests (TypeScript) |
| **Integration Tests** | 63 tests |
| **Coverage** | 100% (prod code) |
| **Python Version** | 3.10+ (SDK), 3.11+ (Server) |
| **Node Version** | 18+ |

## File-by-File Breakdown

### Documentation Site (`site/`, Astro + Starlight)
- **18-page documentation site** — https://agentlens-observe.pages.dev
- **Framework:** Astro 5 + Starlight theme
- **Content:** Getting started, API docs, SDK guides, integrations, FAQ, troubleshooting
- **Deployment:** Cloudflare Pages (automatic builds on push)

### Dashboard (`dashboard/src/`, ~3,500 LOC)

#### Pages (7 files, ~1,400 LOC)
- **`pages/login-page.tsx`** — Email/password login form. Calls auth-api-client. Stores JWT in localStorage via AuthProvider.
- **`pages/api-keys-page.tsx`** — Create, list, delete API keys. Shows key prefix + last used. Full key shown only once on creation.
- **`pages/traces-list-page.tsx`** — List all traces with search, filters, pagination. Uses trace-list-table component. Event listeners for trace_created updates.
- **`pages/trace-detail-page.tsx`** — Single trace with topology graph + span detail panel. Real-time updates via useSSETraces. Pulse animation on running nodes.
- **`pages/trace-compare-page.tsx`** — Side-by-side topology comparison. Lazy-loaded (14KB chunk). Diff algorithm from backend. Color-coded matching.
- **`pages/trace-replay-page.tsx`** — Time-travel replay. Route `#/traces/:id/replay`. Uses use-replay-controls + replay-timeline-scrubber.
- **`pages/alert-rules-page.tsx`** — CRUD UI for alert rules. metric/operator/threshold/mode/window_size/webhook_url fields.
- **`pages/alerts-list-page.tsx`** — View fired alert events. Resolve button. Unresolved count badge from /api/alerts/summary.

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

#### Hooks & Utilities (9 files, ~1,100 LOC)
- **`use-sse-traces.ts`** — EventSource subscription. Listens to span_created + trace_updated + alert_fired. Per-user (auth token sent).
- **`use-live-trace-detail.ts`** — Real-time trace fetching + SSE. Merges API response with stream updates.
- **`use-trace-filters.ts`** — Filter state management (q, status, agent_name, date, cost, sort, order, limit, offset). Updates URL params.
- **`use-replay-controls.ts`** — Replay cursor/timer/speed state machine (1-10x speed, step prev/next, play/pause).
- **`api-client.ts`** — Typed fetch wrapper. Methods: listTraces(), getTrace(), compareTraces(), listAgents(). Error handling + retry logic.
- **`diff-utils.ts`** — LCS matching, color assignment (green/red/blue). Span similarity scoring by name + type + duration.
- **`fetch-with-auth.ts`** — Drop-in fetch wrapper that reads JWT from AuthContext and injects Authorization header.
- **`auth-api-client.ts`** — Typed calls: login(), register(), getMe(), createApiKey(), listApiKeys(), deleteApiKey(). Uses fetch-with-auth.
- **`auth-context.tsx`** — AuthProvider + useAuth hook. Stores JWT in localStorage. Wraps entire app. Redirects unauthenticated users to /login.
- **`alert-api-client.ts`** — Typed calls: createRule(), listRules(), updateRule(), deleteRule(), listAlerts(), resolveAlert(), alertsSummary().

#### Styling
- **`index.css`** — Tailwind setup. CSS variables for dark theme (--slate-*, --blue-*, --red-*, --green-*). Pulse animation on `.animate-pulse`.

#### Config (5 files)
- **`vite.config.ts`** — Build config. Code splitting strategy. React plugin. URL base `/`.
- **`tailwind.config.js`** — Content paths, theme extensions, plugins (forms, animations).
- **`tsconfig.json`** — Strict mode, React JSX. Path alias `@/*` → `src/`.
- **`package.json`** — Dependencies: React 19, Vite 7, React Flow 12, Tailwind 3, Recharts 3, @tanstack/react-virtual, Radix UI, etc.
- **`index.html`** — Root HTML. Mounts app to `#root`.

### Server (`server/`, ~1,400 LOC)

#### Core Entry (1 file, ~200 LOC)
- **`main.py`** — FastAPI app entry. Mounts auth_routes, alert_routes routers. All data routes use get_current_user dependency. Middleware: GZip (>1KB), CORS (all origins).

#### Database Models (3 files, ~200 LOC)
- **`models.py`** — Trace + Span SQLModel tables. Added `user_id` column to Trace. Request schemas: TraceIn, SpanIn, SpansIn, CostIn.
- **`auth_models.py`** — User + ApiKey tables. Request schemas: RegisterIn, LoginIn.
- **`alert_models.py`** — AlertRule + AlertEvent tables. Request schemas: AlertRuleIn, AlertRuleUpdate.

#### Storage & CRUD (3 files, ~450 LOC)
- **`storage.py`** — SQLite interface: init_db(), create_trace(user_id), add_spans_to_trace(), get_trace(), list_traces(user_id), list_agents(user_id). All queries scoped by user_id.
- **`auth_storage.py`** — Auth CRUD: create_user (bcrypt hash), get_user_by_email, verify_password, create_api_key (SHA-256 hash, al_ prefix), validate_api_key, list_user_api_keys, delete_api_key, get_user_by_id.
- **`alert_storage.py`** — Alert CRUD with user_id scoping: create_alert_rule, list_alert_rules, update_alert_rule, delete_alert_rule, create_alert_event, list_alert_events, resolve_alert_event, get_unresolved_alert_count.

#### API Routers (3 files, ~250 LOC)
- **`main.py`** (inline routes) — Traces, spans, agents, OTel, SSE stream.
- **`auth_routes.py`** — /api/auth/* (register, login, me, api-keys CRUD).
- **`alert_routes.py`** — /api/alert-rules CRUD + /api/alerts (list, resolve, summary).

#### Auth Helpers (3 files, ~120 LOC)
- **`auth_jwt.py`** — create_token / decode_token. HS256, 24h expiry. Secret from AGENTLENS_JWT_SECRET env.
- **`auth_deps.py`** — get_current_user FastAPI dependency: Bearer JWT → user; ApiKey header → user. get_optional_user for migration fallback.
- **`auth_seed.py`** — On startup: create admin@agentlens.local if no users; migrate orphan traces/alert_rules/alert_events to admin.

#### Alert Engine (2 files, ~150 LOC)
- **`alert_evaluator.py`** — evaluate_alert_rules(trace_id, agent_name). Evaluates after each trace completes. Absolute + relative thresholds. 60s cooldown per rule. Metric computation: cost, latency, error_rate.

#### Settings & Crypto (2 files, ~140 LOC)
- **`crypto.py`** — Fernet encryption/decryption using cryptography>=42.0. encrypt_key(plaintext_api_key) / decrypt_key(ciphertext). Stored safely in database.
- **`settings_models.py`** — UserSettings SQLModel table. llm_provider, llm_model, api_key_encrypted fields. Per-user configuration for AI Autopsy.

#### LLM & Autopsy (3 files, ~180 LOC)
- **`llm_provider.py`** — LLMProvider abstract base class. OpenAI, Anthropic, Google implementations. Routes to user's configured provider.
- **`autopsy_models.py`** — Autopsy SQLModel table. trace_id, status (pending|completed|error), analysis_text, recommendations JSON.
- **`autopsy_analyzer.py`** — analyze_failed_trace(trace_id, user_settings). Calls user's LLM to analyze failure; generates recommendations. Async with timeout protection.
- **`alert_notifier.py`** — publish_alert_sse() (SSE bus event). fire_webhook() (background thread, urllib, 5s timeout, never raises).

#### SSE Bus (1 file, ~80 LOC)
- **`sse.py`** — Per-user in-memory event bus: publish(event_name, data, user_id). Events: span_created, trace_updated, alert_fired. Subscribers filtered by user_id.

#### Diff Algorithm (1 file, ~100 LOC)
- **`diff.py`** — LCS span tree comparison: compute_diff(left, right). Similarity scoring: name, type, duration. Returns matches, insertions, deletions.

#### OTel Mapper (1 file, ~80 LOC)
- **`otel_mapper.py`** — Pure function: map_otel_trace(otel_payload) → AgentLens TraceIn. Kind mapping: SERVER→agent_run, CLIENT→tool_call, INTERNAL→llm_call. agent_name from resource.attributes["service.name"].

#### Tests (7 files, ~86 tests, ~900 LOC)
- **`test_api_endpoints.py`** — Endpoint tests: POST /traces, POST /spans, GET /traces (filters), GET /compare
- **`test_otel_ingestion.py`** — OTel mapper unit tests + /api/otel/v1/traces integration (8 tests)
- **`test_sse.py`** — Event bus: publish, subscribe, per-user filtering
- **`test_storage.py`** — CRUD: create, list, filter, sort, pagination
- **`test_auth_routes.py`** — Auth flows: register, login, me, API keys, tenant isolation (27 tests)
- **`test_alert_routes.py`** — Alert rule CRUD, evaluation, events, resolve (14 tests)
- **`conftest.py`** — Fixtures: test client, in-memory DB, user fixtures

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

#### Tests (4 files, ~52 tests, ~400 LOC)
- **`test_tracer.py`** — Tracer decorator, span context, parent-child hierarchy, logging
- **`test_transport.py`** — Batch queue, flush, retry logic, concurrent requests (uses X-API-Key header)
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
| `server/auth_routes.py` | 27 | 90% |
| `server/alert_routes.py` | 14 | 88% |
| `server/otel_mapper.py` | 8 | 95% |
| `sdk/tracer.py` | 18 | 92% |
| `sdk/transport.py` | 20 | 85% |
| `sdk/cost.py` | 14 | 100% |
| **Total** | **139** | **86%** |

## Build & Deployment

### Development Build
```bash
cd dashboard && npm run dev      # React dev server (Vite, :5173)
cd server && uvicorn main:app --reload --port 8000
cd sdk && pip install -e ".[dev]"
```

### Production Build
```bash
# Set JWT secret in production
docker run -p 3000:3000 \
  -e AGENTLENS_JWT_SECRET=your-secret \
  tranhoangtu/agentlens-observe:0.6.0
# First run: admin@agentlens.local / changeme — change immediately
```

### PyPI Distribution
```bash
pip install agentlens-observe==0.3.0
```

## Known Limitations & Future Work

### Current (v0.5.0)
- SQLite backend (good for single-machine, limited concurrency)
- No RBAC (all users see full admin panel if is_admin)
- OTel ingestion: OTLP HTTP JSON only (no protobuf/gRPC)
- JWT secret auto-generated if AGENTLENS_JWT_SECRET unset (restarts invalidate tokens)

### Roadmap
- PostgreSQL backend (next milestone)
- TypeScript SDK framework integrations (LangChain.js, LlamaIndex.js)
- RBAC (role-based access, org-level scoping)
