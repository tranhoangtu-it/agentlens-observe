# AgentLens v0.2.0 — System Architecture

## High-Level Architecture

```
┌─────────────────────┐         ┌──────────────────────────┐         ┌──────────────────┐
│   Python Agent      │         │   AgentLens Server       │         │  Browser         │
│                     │         │  (FastAPI + SQLite)      │         │  Dashboard       │
├─────────────────────┤         ├──────────────────────────┤         ├──────────────────┤
│ @agentlens.trace    │────────►│ POST /api/traces         │────────►│ Trace List Page  │
│ @agentlens.span     │         │ (create + 9 UI primitives)        │ (Trace Table)    │
│ agentlens.log()     │         │                          │         │                  │
└─────────────────────┘         │ SSE Bus                  │         │ Trace Detail:    │
                                │ ├─ span_created          │◄────────┤ ├─ Topology Graph │
                                │ └─ trace_updated         │         │ ├─ Span Panel     │
                                │                          │         │ └─ Cost Chart    │
                                │ SQLite (WAL)             │         │                  │
                                │ ├─ Trace (idx)           │         │ Trace Compare:   │
                                │ └─ Span (idx)            │         │ ├─ Left Graph    │
                                │                          │         │ ├─ Right Graph   │
                                │ POST /api/traces/{id}/spans│        │ └─ Diff Panel    │
                                └──────────────────────────┘         └──────────────────┘
                                         ▲
                                         │
                                    Batch Transport
                                    (httpx + queue)
```

## Component Breakdown

### Frontend (React 19 + Vite 7)

**Dashboard** (`dashboard/src/`)

| Component | Purpose |
|-----------|---------|
| `pages/traces-list-page.tsx` | Trace discovery, search, filters, pagination |
| `pages/trace-detail-page.tsx` | Single trace with topology graph + span panel |
| `pages/trace-compare-page.tsx` | Side-by-side diff of two traces (lazy-loaded) |
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

**Hooks** (`lib/`)
- `use-sse-traces.ts` — EventSource subscription, span_created/trace_updated listeners
- `use-live-trace-detail.ts` — Real-time trace detail updates
- `use-trace-filters.ts` — State management for filters
- `api-client.ts` — Typed API calls (fetch wrapper)
- `diff-utils.ts` — Frontend span matching, color coding

**Styling**
- Tailwind 3 (utility classes)
- CSS variables for dark theme
- Radix UI colors (slate, blue, red, green)

### Backend (FastAPI + SQLite)

**API Endpoints** (`server/main.py`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Liveness check |
| `/api/traces` | POST | Create trace (all spans in one go) |
| `/api/traces/{id}/spans` | POST | Append spans (incremental ingestion) |
| `/api/traces` | GET | List traces (q, status, agent, date, cost filters + sort) |
| `/api/traces/{id}` | GET | Fetch single trace with all spans |
| `/api/traces/compare` | GET | Compute diff for two traces |
| `/api/agents` | GET | Distinct agent names for filter dropdown |

**Middleware**
- GZipMiddleware (compress JSON >1KB)
- CORSMiddleware (allow all origins for dev)

**Database** (`server/models.py`)

```python
class Trace:
    id: str [PK]
    agent_name: str [INDEX]
    created_at: datetime [INDEX]
    status: str [INDEX] (running|completed|error)
    span_count: int
    total_cost_usd: float
    total_tokens: int
    duration_ms: int

    # Compound indexes for filtering:
    # (status, created_at)
    # (agent_name, created_at)
    # (total_cost_usd)

class Span:
    id: str [PK]
    trace_id: str [FK, INDEX]
    parent_id: str [NULLABLE, FK]  # DAG tree structure
    name: str
    type: str (llm_call|tool_call|handoff|agent_spawn)
    start_ms: int
    end_ms: int [NULLABLE]  # Running spans have NULL
    input: str [JSON, NULLABLE]
    output: str [JSON, NULLABLE]
    cost_model: str
    cost_input_tokens: int
    cost_output_tokens: int
    cost_usd: float
    metadata_json: str [JSON]
```

**Storage** (`server/storage.py`)
- SQLite connection pool (sqlite3.connect with WAL mode)
- CRUD operations (create_trace, add_spans_to_trace, get_trace, list_traces)
- Query filters: full-text search on agent_name, status, date range, cost range
- Sorting: by created_at, status, cost, span_count (configurable)
- Pagination: limit + offset

**SSE Bus** (`server/sse.py`)
- In-memory event bus
- Subscribers connect via `/api/traces/stream` endpoint
- Events:
  - `span_created`: {trace_id, span}
  - `trace_updated`: {trace_id, status, span_count, total_cost_usd, duration_ms}

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

**Transport** (`transport.py`)
- HTTPClient wrapper (httpx)
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

### Testing

**Server Tests** (`server/tests/`, 38 tests)
- `test_api_endpoints.py` — POST /traces, POST /spans, GET /traces, GET /compare
- `test_sse.py` — Event bus, subscriptions
- `test_storage.py` — CRUD, filtering, sorting

**SDK Tests** (`sdk/tests/`, 52 tests)
- `test_tracer.py` — Decorator, context manager, span hierarchy
- `test_transport.py` — Batch queue, flush, retries
- `test_cost.py` — Pricing calculations

Coverage: >82% (pytest + coverage.py)

## Data Flow

### 1. Trace Creation
```python
@agentlens.trace(name="ResearchAgent")
def run_agent():
    # Decorator captures span hierarchy
    with agentlens.span("web_search", "tool_call"):
        result = search(query)
    return result

# Flow:
# 1. Tracer collects all spans (parent-child links)
# 2. On function exit, transport.batch_queue.put(trace)
# 3. Batch transport flushes every N spans or T seconds
# 4. httpx.post(server_url + "/api/traces", json=trace_pb)
# 5. Server: create_trace() → SQLite → publish("trace_created")
# 6. Browser: EventSource receives span_created, renders nodes
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

## Performance Optimizations

| Layer | Optimization |
|-------|-------------|
| **DB** | Compound indexes (status, created_at), (agent_name, created_at), WAL mode |
| **API** | GZip compression (>1KB), incremental POST /spans |
| **React** | Code splitting (4 chunks), React.memo, lazy-load compare page |
| **Table** | @tanstack/react-virtual (10K rows virtualized) |
| **Transport** | Batch queue, fire-and-forget (non-blocking SDK) |

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
- `SERVER_URL` — Server base URL (SDK config)
- `BATCH_SIZE` — Spans per flush (default: 50)
- `BATCH_INTERVAL` — Flush interval seconds (default: 5)

## Future Scaling

1. **PostgreSQL** — Replace SQLite for multi-server deployments
2. **Time-Series DB** — Separate cost/metrics data to InfluxDB
3. **Message Queue** — Redis/RabbitMQ for high-volume ingestion
4. **Caching** — Redis cache for frequent trace queries
5. **Multi-Tenant** — Auth, tenant isolation, quota enforcement
