# AgentLens v0.6.0 — Product Overview & PDR

**Version:** 0.6.0 | **Release Date:** Mar 2026 | **Status:** Production

## Executive Summary

AgentLens is a self-hosted, open-source AI agent observability platform. Unlike LangSmith (paid, cloud-only) and Langfuse (LLM-focused), AgentLens understands agents: tool calls, handoffs, memory reads, decision trees — not just LLM generations.

**Core Value Proposition:**
- Real-time trace streaming of agent execution
- Visual topology graphs showing agent spawns, tool calls, handoffs
- Trace comparison (side-by-side diff of two runs)
- Cost tracking across 27 LLM models
- Alerting on cost/latency/error_rate anomalies with webhook support
- Multi-tenant authentication (JWT + API key, per-user data isolation)
- Framework integrations (LangChain, CrewAI, AutoGen, LlamaIndex, Google ADK)
- Self-hosted, data-private alternative to cloud observability platforms

## Distribution

- **PyPI (Python SDK):** `pip install agentlens-observe==0.6.0`
- **npm (TypeScript SDK):** `npm install agentlens-observe@0.6.0`
- **Docker:** `docker run -p 3000:3000 tranhoangtu/agentlens-observe:0.6.0`
- **GitHub:** `github.com/tranhoangtu-it/agentlens-observe`
- **Docs Site:** https://agentlens-observe.pages.dev
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
- [x] Python SDK v0.3.0 (3.10+)
- [x] TypeScript SDK v0.1.0 (Node 18+, zero prod dependencies)
- [x] Batch transport with configurable queue + auto-flush
- [x] OpenTelemetry span exporter bridge
- [x] Framework integrations: LangChain, CrewAI, AutoGen, LlamaIndex, Google ADK
- [x] Custom logging via `agentlens.log()` / `agentlens.log()`
- [x] ESM + CJS dual output (TypeScript SDK)

### F8: Multi-Tenant Authentication
- [x] User registration + JWT login (HS256, 24h, Bearer token)
- [x] API key auth (SHA-256 hashed, `al_` prefix, X-API-Key header)
- [x] Per-user data isolation (traces, alert rules, alert events scoped by user_id)
- [x] Dashboard login page, AuthProvider context, protected routes
- [x] SSE per-user event filtering
- [x] Orphan data migration on startup (assign to admin)

### F9: Alerting System
- [x] Alert rules CRUD (`POST/GET/PUT/DELETE /api/alert-rules`)
- [x] Metrics: cost, latency, error_rate with gt/lt/gte/lte operators
- [x] Absolute + relative (rolling baseline) threshold modes
- [x] 60s cooldown per rule to prevent alert storm
- [x] Alert events (`GET /api/alerts`, `PATCH /api/alerts/{id}/resolve`, `GET /api/alerts/summary`)
- [x] Wildcard rules (`agent_name="*"` matches any agent)
- [x] SSE `alert_fired` events for real-time dashboard notifications
- [x] Optional webhook POST delivery (fire-and-forget, 5s timeout)

### F10: Testing & Quality
- [x] 231 tests (86 server + 52 Python SDK + 30 TypeScript SDK + 63 integration)
- [x] 100% production code coverage
- [x] pytest, httpx, respx, vitest test stack

### F11: LLM Settings & Configuration
- [x] User LLM settings endpoints (GET/PUT /api/settings)
- [x] Support for bring-your-own API key (OpenAI, Anthropic, Google, etc.)
- [x] Encrypted credential storage (cryptography>=42.0)
- [x] Dashboard settings page for LLM config
- [x] Per-user credential isolation

### F12: AI Failure Autopsy
- [x] POST/GET/DELETE /api/traces/{id}/autopsy endpoint
- [x] AI-powered analysis of failed traces
- [x] Uses user-configured LLM provider
- [x] Autopsy panel on trace detail page
- [x] Root cause analysis and recommendations

### F13: MCP Protocol Integration
- [x] Python: `agentlens.integrations.mcp.patch_mcp()` for MCP server tracing
- [x] TypeScript: `patchMcp()` from `agentlens/integrations/mcp`
- [x] New span types: `mcp.tool_call`, `mcp.resource_read`, `mcp.prompt_get`
- [x] Support via optional dependency: `pip install agentlens[mcp]`

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
- JWT HS256, 24h token expiry; secret from AGENTLENS_JWT_SECRET env (with startup warning)
- bcrypt password hashing (12 rounds); SHA-256 API key hashing (raw never stored)
- Cross-tenant access returns 404 (not 403) to prevent resource enumeration
- CORS configurable via environment (all origins for localhost dev; production lockdown)
- Webhook SSRF protection (block private IP ranges)
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
| Python SDK | Python 3.10+, httpx, OTel bridge, 27 model pricing |
| TypeScript SDK | Node 18+, AsyncLocalStorage, native fetch, zero prod deps, tsup (ESM+CJS) |
| Testing | pytest, httpx, respx (server/Python SDK); vitest (TypeScript SDK) |
| Deployment | Docker (multi-stage), PyPI, npm |

## Key Features (v0.7.0)

1. **Live trace streaming** — Watch agent think in real-time
2. **Agent topology graph** — Interactive DAG of tool calls, handoffs
3. **Trace comparison** — Side-by-side diff with color-coded matching
4. **Search & filters** — Full-text + status/agent/date/cost filters
5. **Cost tracking** — 27 LLM models priced
6. **Framework integrations** — Auto-instrument LangChain, CrewAI, AutoGen, LlamaIndex, Google ADK
7. **OpenTelemetry ingestion & export** — Receive OTLP HTTP traces; bridge to Datadog, Jaeger, etc.
8. **Batch transport** — High-throughput agent support (Python + TypeScript)
9. **Time-travel replay** — Step through agent execution client-side
10. **TypeScript SDK** — Node 18+, zero prod deps, ESM+CJS, `configure/trace/span/log/addExporter/currentTrace`
11. **Multi-tenant auth** — JWT + API key, per-user isolation, login UI
12. **Alerting** — cost/latency/error_rate rules, absolute + relative thresholds, SSE + webhook
13. **LLM Settings** — BYO API keys for OpenAI, Anthropic, Google with encrypted storage
14. **AI Autopsy** — AI-powered failure analysis using user's LLM provider
15. **MCP Integration** — Trace Model Context Protocol servers (Python + TypeScript)
16. **Self-hosted** — Your data, your machine

## Success Metrics

- **Adoption:** 100+ GitHub stars by end of 2025
- **Performance:** Trace ingestion <100ms, topology render <500ms
- **Reliability:** 99.9% uptime (self-hosted)
- **Coverage:** >82% unit test coverage

## Roadmap (Future)

- [x] Replay/time-travel debugging
- [x] OTel span ingestion (receive spans from other systems)
- [x] TypeScript SDK (v0.1.0 on npm)
- [x] Alerting on behavior anomalies
- [x] Multi-tenant auth (JWT + API key, per-user isolation)
- [ ] PostgreSQL backend
- [ ] RBAC (role-based access, org-level scoping)
- [ ] TypeScript SDK framework integrations (LangChain.js, LlamaIndex.js)

## Constraints & Dependencies

- Python 3.10+ (Python SDK), 3.11+ (Server)
- Node 18+ (Dashboard, TypeScript SDK)
- FastAPI 0.100+
- React 19
- SQLite (current), PostgreSQL (future)
- TypeScript SDK: zero prod dependencies (AsyncLocalStorage, native fetch)
- cryptography>=42.0 (for credential encryption)
- Optional: `pip install agentlens[mcp]` for MCP integration

## Success Criteria

1. **Functional Completeness:** All F1-F10 requirements met ✅
2. **Performance:** P50 trace listing <200ms, compare page <300ms ✅
3. **Code Quality:** 100% prod coverage, 231 tests passing ✅
4. **Security:** bcrypt + SHA-256 + JWT + CORS hardening + SSRF protection ✅
5. **Documentation:** 18-page Astro + Starlight site, GitHub badges, issue templates ✅
