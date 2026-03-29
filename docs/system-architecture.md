# AgentLens v0.9.0 — System Architecture

## High-Level Architecture

```
┌─────────────────────┐
│   Python Agent      │
│ @agentlens.trace    │──────────────────────────────────────────────────────────┐
│ @agentlens.span     │  X-API-Key: al_xxx                                       │
│ agentlens.log()     │                                                          │
└─────────────────────┘                                                          │
                                                                                 ▼
┌─────────────────────┐         ┌──────────────────────────┐         ┌──────────────────┐
│  TypeScript Agent   │         │   AgentLens Server       │         │  Browser         │
│  (Node 18+)         │         │  (FastAPI + SQLite)      │         │  Dashboard       │
├─────────────────────┤         ├──────────────────────────┤         ├──────────────────┤
│ agentlens.trace()   │────────►│ Auth: JWT Bearer / API   │────────►│ Login Page       │
│ agentlens.span()    │         │       Key (X-API-Key)    │         │ Trace List Page  │
│ agentlens.log()     │         │ POST /api/traces         │         │ Alert Rules Page │
└─────────────────────┘         │ POST /api/traces/{id}/spans        │ Alerts List Page │
                                │ POST /api/otel/v1/traces │         │                  │
┌─────────────────────┐         │                          │         │ Trace Detail:    │
│  OTel-instrumented  │         │ SSE Bus (per-user)       │         │ ├─ Topology Graph │
│  system (any lang)  │────────►│ ├─ span_created          │◄────────┤ ├─ Span Panel     │
│  OTLP HTTP JSON     │         │ ├─ trace_updated         │         │ └─ Cost Chart    │
└─────────────────────┘         │ └─ alert_fired           │         │                  │
                                │                          │         │ Trace Replay:    │
                                │ SQLite (WAL)             │         │ ├─ Timeline bar  │
                                │ ├─ User / ApiKey         │         │ └─ Transport ctrl│
                                │ ├─ Trace / Span (idx)   │         └──────────────────┘
                                │ ├─ AlertRule             │
                                │ └─ AlertEvent            │
                                └──────────────────────────┘
                                         ▲
                                    Batch Transport
                                    Python: httpx + queue
                                    TypeScript: fetch + queue
```

## Component Breakdown

### Frontend (React 19 + Vite 7)

**Dashboard** (`dashboard/src/`)

| Component | Purpose |
|-----------|---------|
| `pages/login-page.tsx` | Email/password login; stores JWT in localStorage |
| `pages/api-keys-page.tsx` | Create, list, delete API keys |
| `pages/traces-list-page.tsx` | Trace discovery, search, filters, pagination |
| `pages/trace-detail-page.tsx` | Single trace with topology graph + span panel |
| `pages/trace-compare-page.tsx` | Side-by-side diff of two traces (lazy-loaded) |
| `pages/trace-replay-page.tsx` | Time-travel replay — route `#/traces/:id/replay` |
| `pages/alert-rules-page.tsx` | CRUD UI for alert rules |
| `pages/alerts-list-page.tsx` | View + resolve fired alert events |
| `components/trace-list-table.tsx` | Virtualized table (@tanstack/react-virtual) |
| `components/trace-topology-graph.tsx` | React Flow DAG visualization |
| `components/trace-compare-graphs.tsx` | Dual topology views for comparison |
| `components/span-detail-panel.tsx` | Input, output, cost, duration, metadata |
| `components/span-diff-panel.tsx` | LCS-matched span differences |
| `components/cost-summary-chart.tsx` | Recharts pie chart (cost by model) |
| `components/trace-search-bar.tsx` | Full-text search (q param) |
| `components/trace-filter-controls.tsx` | status, agent_name, from_date, to_date, cost range |
| `components/pagination-controls.tsx` | limit, offset controls |

**UI Primitives** (`components/ui/`) — shadcn/ui + Radix UI
- `badge.tsx` — Status badges (completed, running, error)
- `button.tsx` — Action buttons (delete, export, etc.)
- `card.tsx` — Container for panels
- `input.tsx` — Text search, filter inputs
- `skeleton.tsx` — Loading placeholders
- `table.tsx` — Virtualized table base
- `separator.tsx` — Visual dividers
- `tooltip.tsx` — Hover help
- `scroll-area.tsx` — Custom scrollbars

**Hooks & Utilities** (`lib/`)
- `use-sse-traces.ts` — EventSource subscription, span_created/trace_updated/alert_fired listeners
- `use-live-trace-detail.ts` — Real-time trace detail updates
- `use-trace-filters.ts` — State management for filters
- `use-replay-controls.ts` — Replay cursor/timer/speed state machine
- `api-client.ts` — Typed API calls (fetch wrapper)
- `diff-utils.ts` — Frontend span matching, color coding
- `fetch-with-auth.ts` — Fetch wrapper that injects Authorization header from auth context
- `auth-api-client.ts` — Typed auth calls: login, register, getMe, createApiKey, listApiKeys, deleteApiKey
- `auth-context.tsx` — React context: AuthProvider, useAuth hook; token persisted in localStorage
- `alert-api-client.ts` — Typed alert calls: createRule, listRules, updateRule, deleteRule, listAlerts, resolveAlert, alertsSummary

**Replay Components** (`components/`)
- `replay-transport-controls.tsx` — Play/pause, step prev/next, speed selector
- `replay-timeline-scrubber.tsx` — Gantt bars + range slider for cursor control

**Styling**
- Tailwind 3 (utility classes)
- CSS variables for dark theme
- Radix UI colors (slate, blue, red, green)

### Backend (FastAPI + SQLite)

**API Endpoints**

All endpoints except `/api/health` and `/api/auth/*` registration/login require `Authorization: Bearer <jwt>` or `X-API-Key: al_...`.

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/health` | GET | Public | Liveness check |
| `/api/auth/register` | POST | Public | Create user account |
| `/api/auth/login` | POST | Public | Email/password login → JWT |
| `/api/auth/me` | GET | JWT/ApiKey | Current user profile |
| `/api/auth/api-keys` | POST | JWT/ApiKey | Create API key (returned once) |
| `/api/auth/api-keys` | GET | JWT/ApiKey | List API keys (prefix only) |
| `/api/auth/api-keys/{id}` | DELETE | JWT/ApiKey | Revoke API key |
| `/api/traces` | POST | JWT/ApiKey | Create trace (all spans in one go) |
| `/api/traces/{id}/spans` | POST | JWT/ApiKey | Append spans (incremental) |
| `/api/traces` | GET | JWT/ApiKey | List traces (q, status, agent, date, cost + sort) |
| `/api/traces/{id}` | GET | JWT/ApiKey | Fetch single trace with all spans |
| `/api/traces/compare` | GET | JWT/ApiKey | Compute diff for two traces |
| `/api/agents` | GET | JWT/ApiKey | Distinct agent names for filter dropdown |
| `/api/otel/v1/traces` | POST | JWT/ApiKey | OTLP HTTP JSON ingestion |
| `/api/alert-rules` | POST | JWT/ApiKey | Create alert rule |
| `/api/alert-rules` | GET | JWT/ApiKey | List alert rules (agent_name, metric, enabled filters) |
| `/api/alert-rules/{id}` | PUT | JWT/ApiKey | Update alert rule |
| `/api/alert-rules/{id}` | DELETE | JWT/ApiKey | Delete alert rule |
| `/api/alerts` | GET | JWT/ApiKey | List alert events (agent_name, resolved, pagination) |
| `/api/alerts/{id}/resolve` | PATCH | JWT/ApiKey | Mark alert event resolved |
| `/api/alerts/summary` | GET | JWT/ApiKey | Unresolved alert count |
| `/api/settings` | GET | JWT/ApiKey | Get user LLM settings (provider, model) |
| `/api/settings` | PUT | JWT/ApiKey | Update user LLM settings (encrypted storage) |
| `/api/traces/{id}/autopsy` | POST | JWT/ApiKey | Request AI failure analysis for trace |
| `/api/traces/{id}/autopsy` | GET | JWT/ApiKey | Retrieve autopsy results (cached) |
| `/api/traces/{id}/autopsy` | DELETE | JWT/ApiKey | Delete autopsy analysis |
| `/api/prompts` | POST | JWT/ApiKey | Create prompt template |
| `/api/prompts` | GET | JWT/ApiKey | List prompt templates |
| `/api/prompts/{id}` | GET | JWT/ApiKey | Get prompt with all versions |
| `/api/prompts/{id}/versions` | POST | JWT/ApiKey | Create new prompt version |
| `/api/prompts/{id}/diff` | GET | JWT/ApiKey | Diff two versions (v1, v2 query params) |
| `/api/eval/criteria` | POST | JWT/ApiKey | Create evaluation criteria |
| `/api/eval/criteria` | GET | JWT/ApiKey | List evaluation criteria |
| `/api/eval/criteria/{id}` | PUT | JWT/ApiKey | Update evaluation criteria |
| `/api/eval/criteria/{id}` | DELETE | JWT/ApiKey | Delete evaluation criteria |
| `/api/eval/run` | POST | JWT/ApiKey | Run evaluation on traces |
| `/api/eval/runs` | GET | JWT/ApiKey | List evaluation runs |
| `/api/eval/scores` | GET | JWT/ApiKey | Get eval scores for trace |

**Middleware**
- GZipMiddleware (compress JSON >1KB)
- CORSMiddleware — Configurable via `AGENTLENS_CORS_ORIGINS` env (defaults: `localhost:3000,localhost:5173` for dev)
  - Allowed Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
  - Allowed Headers: Authorization, Content-Type, X-API-Key

**Database** (`server/models.py`, `server/auth_models.py`, `server/alert_models.py`, `server/prompt_models.py`, `server/eval_models.py`)

```python
class User:                        # auth_models.py
    id: str [PK]
    email: str [UNIQUE, INDEX]
    password_hash: str             # bcrypt 12 rounds
    display_name: str [NULLABLE]
    is_admin: bool
    created_at: datetime
    updated_at: datetime

class ApiKey:                      # auth_models.py
    id: str [PK]
    user_id: str [INDEX]
    key_hash: str                  # SHA-256 of raw key (never stored plain)
    key_prefix: str                # First 8 chars "al_xxxx..."
    name: str
    created_at: datetime
    last_used_at: datetime [NULLABLE]
    # Index: (key_hash)

class Trace:                       # models.py
    id: str [PK]
    user_id: str [NULLABLE, INDEX] # owner (set on ingestion)
    agent_name: str [INDEX]
    created_at: datetime [INDEX]
    status: str [INDEX] (running|completed|error)
    span_count: int
    total_cost_usd: float
    total_tokens: int
    duration_ms: int
    # Compound indexes: (status, created_at), (agent_name, created_at)

class Span:                        # models.py
    id: str [PK]
    trace_id: str [FK, INDEX]
    parent_id: str [NULLABLE, FK]
    name: str
    type: str (llm_call|tool_call|handoff|agent_spawn|mcp.tool_call|mcp.resource_read|mcp.prompt_get)
    start_ms: int
    end_ms: int [NULLABLE]
    input: str [JSON, NULLABLE]
    output: str [JSON, NULLABLE]
    cost_model: str
    cost_input_tokens: int
    cost_output_tokens: int
    cost_usd: float
    metadata_json: str [JSON]

class AlertRule:                   # alert_models.py
    id: str [PK]
    user_id: str [NULLABLE, INDEX]
    name: str
    agent_name: str [INDEX]        # "*" = wildcard (all agents)
    metric: str                    # cost|latency|error_rate|missing_span
    operator: str                  # gt|lt|gte|lte
    threshold: float
    mode: str                      # absolute|relative
    window_size: int               # last N traces for rolling baseline
    enabled: bool [INDEX]
    webhook_url: str [NULLABLE]
    created_at: datetime [INDEX]
    # Compound index: (agent_name, metric)

class AlertEvent:                  # alert_models.py
    id: str [PK]
    rule_id: str [INDEX]
    trace_id: str [INDEX]
    user_id: str [NULLABLE, INDEX]
    agent_name: str [INDEX]
    metric: str
    value: float
    threshold: float
    message: str
    resolved: bool [INDEX]
    created_at: datetime [INDEX]
    # Compound index: (rule_id, created_at)

class UserSettings:                # settings_models.py
    id: str [PK]
    user_id: str [UNIQUE, INDEX]
    llm_provider: str              # "openai"|"anthropic"|"google"|"custom"
    llm_model: str                 # Model name (e.g., "gpt-4")
    api_key_encrypted: str         # Encrypted with cryptography.Fernet
    api_key_iv: str [NULLABLE]     # IV for encryption
    created_at: datetime
    updated_at: datetime

class Autopsy:                     # autopsy_models.py
    id: str [PK]
    trace_id: str [INDEX]
    user_id: str [NULLABLE, INDEX]
    status: str                    # "pending"|"completed"|"error"
    analysis_text: str [NULLABLE]  # AI-generated failure analysis
    recommendations: str [NULLABLE] # JSON array of recommendations
    error_message: str [NULLABLE]  # Error details if failed
    created_at: datetime
    updated_at: datetime

class PromptTemplate:              # prompt_models.py
    id: str [PK]
    user_id: str [INDEX]
    name: str
    latest_version: int
    created_at: datetime
    updated_at: datetime
    # Index: (user_id, name) UNIQUE

class PromptVersion:               # prompt_models.py
    id: str [PK]
    prompt_id: str [INDEX]
    user_id: str [INDEX]
    version: int
    content: str
    variables_json: str            # JSON array of variable names
    metadata_json: str             # JSON object of arbitrary metadata
    created_at: datetime
    # Index: (prompt_id, version) UNIQUE

class EvalCriteria:                # eval_models.py
    id: str [PK]
    user_id: str [INDEX]
    name: str
    description: str
    rubric: str
    score_type: str                # "numeric" (1-5) | "binary" (pass/fail)
    agent_name: str                # "*" = all agents, otherwise specific agent name
    auto_eval: bool                # auto-evaluate on trace completion
    enabled: bool [INDEX]
    created_at: datetime
    updated_at: datetime
    # Index: (user_id, agent_name)

class EvalRun:                     # eval_models.py
    id: str [PK]
    criteria_id: str [INDEX]
    trace_id: str [INDEX]
    user_id: str [INDEX]
    score: float                   # 1-5 (numeric) or 0/1 (binary)
    reasoning: str                 # LLM judge's explanation
    llm_provider: str              # Provider used for evaluation
    llm_model: str                 # Model used for evaluation
    prompt_name: str [NULLABLE]    # Optional prompt template used
    prompt_version: int [NULLABLE] # Optional prompt version used
    created_at: datetime
    # Index: (criteria_id, trace_id), (user_id, created_at)
```

**Storage** (`server/storage.py`)
- SQLite connection pool (sqlite3.connect with WAL mode)
- CRUD operations (create_trace, add_spans_to_trace, get_trace, list_traces)
- Query filters: full-text search on agent_name, status, date range, cost range
- Sorting: by created_at, status, cost, span_count (configurable)
- Pagination: limit + offset

**SSE Bus** (`server/sse.py`)
- In-memory per-user event bus
- Subscribers connect via `/api/traces/stream` endpoint (auth required)
- Per-user filtering: events only delivered to the owning user's SSE connection
- Events:
  - `span_created`: {trace_id, span}
  - `trace_updated`: {trace_id, status, span_count, total_cost_usd, duration_ms}
  - `alert_fired`: {alert_id, rule_name, agent_name, metric, message}

**Auth Modules** (`server/auth_*.py`)
- `auth_models.py` — User + ApiKey SQLModel tables + request schemas
- `auth_storage.py` — CRUD: create_user, get_user_by_email, verify_password (bcrypt), create_api_key, validate_api_key (SHA-256 lookup), list_user_api_keys, delete_api_key
- `auth_jwt.py` — create_token / decode_token (PyJWT, HS256, 24h expiry); secret from AGENTLENS_JWT_SECRET env or auto-generated
- `auth_deps.py` — get_current_user FastAPI dependency: reads authorization from:
  1. `Authorization: Bearer <jwt>` header (dashboard)
  2. `Authorization: ApiKey <al_xxx>` header (SDK with API key)
  3. `X-API-Key: <al_xxx>` header (SDK convenience)
  4. `?token=<jwt>` query parameter (SSE/EventSource fallback — required since EventSource can't set headers)
- `auth_routes.py` — /api/auth/* endpoints
- `auth_seed.py` — Creates admin@agentlens.local on first run; migrates orphan traces/alerts to admin

**Alert Modules** (`server/alert_*.py`)
- `alert_models.py` — AlertRule + AlertEvent SQLModel tables + request schemas (AlertRuleIn, AlertRuleUpdate)
- `alert_storage.py` — CRUD with user_id scoping: create_alert_rule, list_alert_rules, update_alert_rule, delete_alert_rule, create_alert_event, list_alert_events, resolve_alert_event, get_unresolved_alert_count
- `alert_evaluator.py` — evaluate_alert_rules(trace_id, agent_name): called after each trace completion; supports absolute + relative (rolling baseline) thresholds; 60s cooldown per rule
- `alert_notifier.py` — publish_alert_sse() + fire_webhook() (fire-and-forget background thread, 5s timeout, stdlib urllib)

**Settings & Crypto Modules** (`server/settings_*.py`, `server/crypto.py`)
- `settings_models.py` — UserSettings SQLModel table with llm_provider, llm_model, encrypted api_key
- `settings_storage.py` — CRUD: get_user_settings, update_user_settings (user_id scoped)
- `crypto.py` — Fernet encryption/decryption for API keys; `encrypt_key(api_key) -> ciphertext`, `decrypt_key(ciphertext) -> api_key`

**Autopsy Modules** (`server/autopsy_*.py`, `server/llm_provider.py`)
- `autopsy_models.py` — Autopsy SQLModel table with status, analysis_text, recommendations
- `autopsy_storage.py` — CRUD: create_autopsy, get_autopsy, list_autopsies, delete_autopsy (user_id scoped)
- `autopsy_analyzer.py` — analyze_failed_trace(trace_id, llm_provider, llm_model, api_key) → calls user's LLM with failure context
- `llm_provider.py` — LLMProvider abstract class; OpenAI, Anthropic, Google implementations; routes to user's configured provider

**Diff Algorithm** (`server/diff.py`)
- LCS (Longest Common Subsequence) on span tree
- Match spans by name, type, duration similarity
- Color-code: green (match), red (deletion), blue (insertion)

### Python SDK (`sdk/agentlens/`)

**Tracer** (`tracer.py`)
- `Tracer.trace()` — Decorator for agent functions
- `Tracer.span()` — Context manager for child spans
- `Tracer.log()` — Add log entries to span metadata
- `Tracer.configure()` — Set server_url, batch settings
- `Tracer.add_exporter()` — Attach OTel or custom exporters
- `Tracer.add_processor()` — Attach span processors for lifecycle hooks
- `SpanProcessor` protocol — `on_start(span)` / `on_end(span)` hooks

**Transport** (`transport.py`)
- HTTPClient wrapper (httpx)
- API key support: `set_api_key(key)` function configures `X-API-Key` header for authenticated requests
- Batch queue (configurable batch_size, batch_interval)
- Auto-flush on timer or queue full
- Fire-and-forget (non-blocking)

**Cost** (`cost.py`)
- Pricing table: 27 LLM models (GPT-4.1, Claude 4, Gemini 2.0, DeepSeek, Llama 3.3, etc.)
- Per-token costs (input, output)
- Helper: `calculate_cost(model, input_tokens, output_tokens) -> float`

**Exporters** (`exporters/otel.py`)
- SpanExporter protocol (Python std)
- Converts AgentLens spans → OTel trace format
- Send to OTel collector

**Integrations** (`integrations/`)
- `langchain.py` — AgentLensCallbackHandler
- `crewai.py` — patch_crewai()
- `autogen.py` — patch_autogen()
- `llamaindex.py` — AgentLensCallbackHandler
- `google_adk.py` — patch_google_adk()
- `mcp.py` — patch_mcp() for Model Context Protocol; traces mcp.tool_call, mcp.resource_read, mcp.prompt_get spans

### TypeScript SDK (`sdk-ts/src/`)

**Runtime requirements:** Node 18+ (AsyncLocalStorage, native fetch). Zero production dependencies. Dual ESM + CJS output via tsup.

**Public API** (`index.ts` — singleton exports)

| Function | Description |
|----------|-------------|
| `configure(config: TracerConfig)` | Set `serverUrl`, `apiKey` (optional), batch options |
| `trace(agentName, fn, opts?)` | Run `fn` inside a named trace context |
| `span(name, spanType?)` | Create child span; call `.enter()` / `.exit()` |
| `log(message, extra?)` | Add timestamped log to the active span |
| `addExporter(exporter)` | Register a custom `SpanExporter` |
| `currentTrace()` | Return the active `ActiveTrace`, if any |

**Tracer** (`tracer.ts`)
- `Tracer` class with `AsyncLocalStorage` for context propagation
- `ActiveTrace` — holds root span + child spans
- `SpanContext` — `.enter()`, `.exit()`, `.setOutput()`, `.setCost()`

**Transport** (`transport.ts`)
- `postTrace()` — POST all spans to `/api/traces` (with optional X-API-Key header if configured)
- `postSpans()` — POST incremental spans to `/api/traces/{id}/spans` (with optional X-API-Key header if configured)
- `flushBatch()` — Flush pending spans queue
- API key support: `apiKey` in `TracerConfig` configures `X-API-Key` header for authenticated requests

**Cost** (`cost.ts`)
- `calculateCost(model, inputTokens, outputTokens) -> number`
- Mirrors Python SDK pricing table

**Types** (`types.ts`)
- `TracerConfig`, `SpanData`, `TracePayload`, `SpansPayload`, `LogEntry`, `CostData`, `SpanExporter`, `ISpanContext`

**Integrations** (`integrations/`)
- `mcp.ts` — patchMcp() function for Model Context Protocol; auto-traces MCP client operations (tool_call, resource_read, prompt_get)

**Testing** — 30 tests with vitest

### Testing

**Server Tests** (`server/tests/`, 86 tests, 86% coverage)
- `test_api_endpoints.py` — POST /traces, POST /spans, GET /traces, GET /compare
- `test_otel_ingestion.py` — POST /api/otel/v1/traces, otel_mapper unit tests (8 tests)
- `test_sse.py` — Event bus, subscriptions, per-user filtering
- `test_storage.py` — CRUD, filtering, sorting
- `test_auth_routes.py` — Register, login, me, API keys, tenant isolation (27 tests)
- `test_alert_routes.py` — Alert rule CRUD, alert events, resolve, summary (14 tests)

**Python SDK Tests** (`sdk/tests/`)
- `test_tracer.py` — Decorator, context manager, span hierarchy
- `test_transport.py` — Batch queue, flush, retries
- `test_cost.py` — Pricing calculations

**TypeScript SDK Tests** (`sdk-ts/tests/`, 30 tests, vitest)
- Tracer context propagation, span lifecycle
- Transport batch queue and flush
- Cost calculation accuracy

Coverage: 86% (pytest + coverage.py)

## Data Flow

### 1. Trace Creation (Authenticated)
```python
agentlens.configure(server_url="http://localhost:3000", api_key="al_...")

@agentlens.trace(name="ResearchAgent")
def run_agent():
    with agentlens.span("web_search", "tool_call"):
        result = search(query)
    return result

# Flow:
# 1. Tracer collects all spans (parent-child links)
# 2. On function exit, transport.batch_queue.put(trace)
# 3. Batch transport flushes every N spans or T seconds
# 4. httpx.post(..."/api/traces", headers={"X-API-Key": "al_..."}, json=trace_pb)
# 5. Server: auth_deps.get_current_user validates API key → user
# 6. create_trace(user_id=user.id) → SQLite
# 7. evaluate_alert_rules(trace_id, agent_name) → fires AlertEvents if triggered
# 8. publish("trace_created", user_id=...) → SSE filtered to owning user
# 9. Browser: EventSource receives span_created, renders nodes
```

### 1b. Alert Evaluation Flow
```
Trace arrives → evaluate_alert_rules()
  ↓
For each enabled rule matching agent_name (or "*"):
  1. Check cooldown (skip if last event < 60s ago)
  2. Compute metric: cost | latency | error_rate
  3. If mode=relative: compute rolling baseline avg (last N traces)
  4. Compare value op threshold (gt|lt|gte|lte)
  5. If triggered: create AlertEvent → publish SSE "alert_fired"
                   + fire webhook POST (background thread, 5s timeout)
```

### 2. Real-Time Streaming
```python
transport.add_span(span)  # Mid-execution
# Flow:
# 1. POST /api/traces/{trace_id}/spans (incremental)
# 2. Server: add_spans_to_trace() + publish("span_created", {span})
# 3. Browser: EventSource listener updates topology graph
# 4. Pulse animation on running nodes
```

### 3. Trace Comparison
```
GET /api/traces/compare?left={id1}&right={id2}
# Flow:
# 1. Server: get_trace_pair(id1, id2)
# 2. diff.compute_diff(trace1, trace2)  → LCS matching
# 3. Return {left, right, matches}
# 4. Browser: React Flow renders both topologies
# 5. Span diff panel shows insertions/deletions/matches
```

**Plugin System** (`server/plugin_protocol.py`, `server/plugin_loader.py`)
- `ServerPlugin` protocol — `on_trace_created()`, `on_trace_completed()`, `register_routes(app)`
- Auto-discovery from `server/plugins/` directory
- Each plugin module exposes a module-level `plugin` instance
- Plugins notified after trace ingestion and completion
- Error handling: plugin exceptions never crash server (logged as warnings)

**Prompt Versioning** (`server/prompt_models.py`, `server/prompt_storage.py`, `server/prompt_routes.py`)
- `PromptTemplate` — Named prompt owned by user, tracks latest version
- `PromptVersion` — Immutable snapshot at version N with content, variables, metadata
- CRUD APIs: create template, list templates, add version, get specific version, diff versions
- Unified diff algorithm for version comparison (unified_diff format)
- Dashboard: Prompt Registry page with version viewer and diff UI

**Evaluation System** (`server/eval_models.py`, `server/eval_storage.py`, `server/eval_runner.py`, `server/eval_routes.py`)
- `EvalCriteria` — Named evaluation rubric (numeric 1-5 or binary pass/fail scoring)
- `EvalRun` — Result of LLM judge assessment (score + reasoning)
- LLM-as-Judge pattern: build prompt from criteria + trace, call user's LLM, parse JSON response
- Auto-eval on trace completion (opt-in per criteria)
- Dashboard: Eval Dashboard with criteria management and score visualization
- Supports both user-provided and built-in LLM providers

### Replay Sandbox (`server/replay_*.py`, `dashboard/src/components/replay-*`)

**Models** (`server/replay_models.py`)
- `ReplaySession` — Edited span snapshots tied to original trace
  - Fields: id, trace_id, user_id, name, base_span_id, edited_spans (JSON), timestamps
  - Indexes: (trace_id, user_id), (user_id, created_at)

**Storage** (`server/replay_storage.py`)
- `create_replay_session(trace_id, user_id, name)` — Create session
- `get_replay_session(session_id, user_id)` — Fetch with ownership
- `list_replay_sessions(trace_id, user_id)` — List all for trace
- `update_replay_session_edits(session_id, edited_spans)` — Update span edits
- `delete_replay_session(session_id, user_id)` — Delete session

**Routes** (`server/replay_routes.py`)
- `POST /api/replay-sessions` — Create session
- `GET /api/traces/{id}/replay-sessions` — List by trace
- `GET /api/replay-sessions/{id}` — Fetch session
- `PUT /api/replay-sessions/{id}` — Update edits
- `DELETE /api/replay-sessions/{id}` — Delete session

**Dashboard Components**
- `replay-sandbox-controls.tsx` — Mode toggle (View/Sandbox), save/load buttons
- `replay-span-editor.tsx` — JSON editor for input/output editing
- `replay-timeline-view.tsx` — Visual timeline with edited spans highlighted
- `replay-session-list.tsx` — Saved sessions management UI

### Go CLI Tool (`cli/`)

**Structure**
- `main.go` — Entry point, command dispatch
- `commands/{traces,config,push}.go` — Command implementations
- `api/client.go` — HTTP client wrapper
- `config/config.go` — Config file management (~/.agentlens/config.json)

**Commands**
- `traces list` — List traces (filters: status, agent, limit)
- `traces show <id>` — Display trace details (formats: json, table, tree)
- `traces tail` — Stream traces in real-time (SSE)
- `traces diff` — Compare two traces (unified diff output)
- `push` — Read trace JSON from stdin, POST to server
- `config set/show` — Manage config file

**Technology**
- Framework: Cobra (CLI framework)
- Config: viper (file management)
- Output: tablewriter (ASCII tables), stdlib json
- Streaming: SSE listener for tail command

### VS Code Extension (`vscode-extension/`)

**Architecture**
- `extension.ts` — Entry point, command registration
- `sidebar-provider.ts` — TreeView data provider (trace list)
- `webview-provider.ts` — WebView for trace detail inspection
- `status-bar.ts` — Status indicator (Connected/Disconnected)
- `api-client.ts` — API call wrapper

**Features**
- **Sidebar TreeView** — List recent traces grouped by agent, expandable
- **Detail WebView** — Show trace topology, span details, JSON viewer
- **Status Bar** — Connection status indicator
- **Context Menu** — Open trace, open in browser, compare, delete, export
- **Configuration** — Settings: agentlens.endpoint, agentlens.apiKey

**Technology**
- Extension API: Visual Studio Code Extension API
- UI: WebView (HTML/CSS/JavaScript)
- Graph: React Flow component (reused from dashboard)
- Build: TypeScript + esbuild, published as VSIX

## Performance Optimizations

| Layer | Optimization |
|-------|-------------|
| **DB** | Compound indexes (status, created_at), (agent_name, created_at), WAL mode |
| **API** | GZip compression (>1KB), incremental POST /spans |
| **React** | Code splitting (4 chunks), React.memo, lazy-load compare page |
| **Table** | @tanstack/react-virtual (10K rows virtualized) |
| **Transport** | Batch queue, fire-and-forget (non-blocking SDK) |
| **Replay Sessions** | JSON blobs, no re-execution cost |
| **CLI Streaming** | SSE for `traces tail`, efficient polling |
| **VS Code Sidebar** | 5s poll interval (configurable), cached responses |

## Deployment Architecture

### Docker Multi-Stage Build
```dockerfile
# Stage 1: Node build
FROM node:20-alpine
COPY dashboard /app/dashboard
RUN cd /app/dashboard && npm install && npm run build

# Stage 2: Python runtime
FROM python:3.11-slim
COPY --from=0 /app/dashboard/dist /app/server/static
COPY server /app/server
RUN pip install -r requirements.txt
EXPOSE 3000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000"]
```

### Environment Variables
- `AGENTLENS_JWT_SECRET` — JWT signing secret (auto-generated if unset; set in production)
- `SERVER_URL` — Server base URL (SDK config)
- `BATCH_SIZE` — Spans per flush (default: 50)
- `BATCH_INTERVAL` — Flush interval seconds (default: 5)

## Future Scaling

1. **PostgreSQL** — Replace SQLite for multi-server deployments
2. **Time-Series DB** — Separate cost/metrics data to InfluxDB
3. **Message Queue** — Redis/RabbitMQ for high-volume ingestion
4. **Caching** — Redis cache for frequent trace queries
5. **TypeScript SDK Framework Integrations** — LangChain.js, LlamaIndex.js, Vercel AI SDK
6. **RBAC** — Role-based access control, org-level tenant scoping
