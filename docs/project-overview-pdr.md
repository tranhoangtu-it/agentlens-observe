# AgentLens v0.2.0 — Product Overview & PDR

**Version:** 0.2.0 | **Release Date:** Feb 2025 | **Status:** Production

## Executive Summary

AgentLens is a self-hosted, open-source AI agent observability platform. Unlike LangSmith (paid, cloud-only) and Langfuse (LLM-focused), AgentLens understands agents: tool calls, handoffs, memory reads, decision trees — not just LLM generations.

**Core Value Proposition:**
- Real-time trace streaming of agent execution
- Visual topology graphs showing agent spawns, tool calls, handoffs
- Trace comparison (side-by-side diff of two runs)
- Cost tracking across 27 LLM models
- Framework integrations (LangChain, CrewAI, AutoGen, LlamaIndex, Google ADK)
- Self-hosted, data-private alternative to cloud observability platforms

## Distribution

- **PyPI:** `pip install agentlens-observe==0.2.0`
- **Docker:** `docker run -p 3000:3000 tranhoangtu/agentlens:0.2.0`
- **GitHub:** `github.com/tranhoangtu-it/agentlens`
- **License:** MIT

## Functional Requirements

### F1: Trace Management
- [x] Create traces via API (`POST /api/traces`)
- [x] Incremental span ingestion (`POST /api/traces/{id}/spans`)
- [x] Retrieve trace details (`GET /api/traces/{id}`)
- [x] List traces with full-text search, filters, sorting, pagination

### F2: Real-Time Updates (SSE)
- [x] `span_created` events per new span
- [x] `trace_updated` aggregate events (cost, duration, status)
- [x] Browser clients subscribe via EventSource

### F3: Trace Comparison
- [x] Side-by-side topology graphs (React Flow)
- [x] Server-side LCS span tree diff
- [x] Color-coded line diff (matching spans, insertions, deletions)
- [x] Route: `#/compare/:left/:right`

### F4: UI/UX
- [x] Dashboard UX overhaul with shadcn/ui design system
- [x] Sidebar navigation, dark theme (CSS variables)
- [x] Trace list with search, status/agent/date/cost filters
- [x] Sortable columns, pagination
- [x] Span detail panel (input, output, cost, duration)
- [x] Cost summary chart (Recharts)
- [x] Virtualized table (@tanstack/react-virtual)

### F5: Pricing & Cost Tracking
- [x] 27 LLM models: GPT-4.1, Claude 4, Gemini 2.0, DeepSeek, Llama 3.3, etc.
- [x] Per-span cost calculation
- [x] Trace-level cost aggregation

### F6: SDK & Integrations
- [x] Python SDK v0.2.0 (3.10+)
- [x] Batch transport with configurable queue + auto-flush
- [x] OpenTelemetry span exporter bridge
- [x] Framework integrations: LangChain, CrewAI, AutoGen, LlamaIndex, Google ADK
- [x] Custom logging via `agentlens.log()`

### F7: Testing & Quality
- [x] 38 server tests (pytest, httpx, respx)
- [x] 52 SDK tests
- [x] >82% code coverage

## Non-Functional Requirements

### Performance
- SQLite with WAL mode (optimized for concurrent reads)
- Compound DB indexes on (status, created_at), (agent_name, created_at), (total_cost_usd)
- GZip middleware for JSON compression
- Code splitting (4 chunks: index 282KB, recharts 335KB, react-flow 232KB, compare 14KB)
- React.memo on expensive components
- Lazy-loaded compare page

### Scalability
- Batch transport with auto-flush (configurable batch_size, batch_interval)
- Incremental span ingestion (avoid single large POST)
- SQLite WAL supports thousands of traces/day
- Future: PostgreSQL backend

### Security
- CORS enabled (all origins for localhost dev)
- HTTPS recommended for production
- No user auth (v0.2.0) — assumes private network
- OTel bridge for multi-backend export

### Reliability
- Fire-and-forget trace ingestion (non-blocking)
- SSE graceful disconnection handling
- SQLite transactions ensure data integrity

## Architecture Overview

```
Your Agent (Python)          AgentLens Server          Browser Dashboard
      │                            │                         │
      ├── @agentlens.trace ──────► POST /api/traces ───────► Live topology graph
      │   (fire-and-forget)        │                         │
      │   flush_span() ──────────► POST /api/traces/:id/spans► Real-time node updates
      │                            │                         │
      │                            ├── SSE stream ──────────► span_created events
      │                            │                         │
      └── Never blocked            └── SQLite + WAL          └── Cost breakdown + diff
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Dashboard | React 19, Vite 7, React Flow 12, Tailwind 3, Recharts 3, Radix UI, @tanstack/react-virtual |
| Server | Python 3.11+, FastAPI, SQLite (WAL), SQLModel, SSE |
| SDK | Python 3.10+, httpx, OTel bridge, 27 model pricing |
| Testing | pytest, httpx, respx |
| Deployment | Docker (multi-stage), PyPI |

## Key Features (v0.2.0)

1. **Live trace streaming** — Watch agent think in real-time
2. **Agent topology graph** — Interactive DAG of tool calls, handoffs
3. **Trace comparison** — Side-by-side diff with color-coded matching
4. **Search & filters** — Full-text + status/agent/date/cost filters
5. **Cost tracking** — 27 LLM models priced
6. **Framework integrations** — Auto-instrument LangChain, CrewAI, AutoGen, LlamaIndex, Google ADK
7. **OpenTelemetry export** — Bridge to Datadog, Jaeger, etc.
8. **Batch transport** — High-throughput agent support
9. **Self-hosted** — Your data, your machine
10. **90+ tests** — >82% coverage

## Success Metrics

- **Adoption:** 100+ GitHub stars by end of 2025
- **Performance:** Trace ingestion <100ms, topology render <500ms
- **Reliability:** 99.9% uptime (self-hosted)
- **Coverage:** >82% unit test coverage

## Roadmap (Future)

- [ ] Replay/time-travel debugging
- [ ] OTel span ingestion (receive spans from other systems)
- [ ] PostgreSQL backend
- [ ] TypeScript SDK
- [ ] Alerting on behavior anomalies
- [ ] Multi-tenant auth

## Constraints & Dependencies

- Python 3.10+ (SDK), 3.11+ (Server)
- Node 18+ (Dashboard)
- FastAPI 0.100+
- React 19
- SQLite (current), PostgreSQL (future)

## Success Criteria

1. **Functional Completeness:** All F1-F7 requirements met ✅
2. **Performance:** P50 trace listing <200ms, compare page <300ms ✅
3. **Code Quality:** >82% coverage, zero critical bugs ✅
4. **User Satisfaction:** Clear documentation, example projects ✅
