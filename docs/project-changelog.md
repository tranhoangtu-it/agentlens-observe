# AgentLens Changelog

All notable changes documented. Format follows [Keep a Changelog](https://keepachangelog.com/).

## [0.4.0] — 2026-02-28

**Version:** 0.4.0 | **Status:** Production | **Release Type:** Major Feature Release

### Added

#### TypeScript SDK (npm: `agentlens-observe@0.1.0`)
- **Package:** `agentlens-observe` v0.1.0 published to npm
- **Runtime:** Node 18+ (AsyncLocalStorage, native fetch), zero production dependencies
- **Public API:** `configure()`, `trace()`, `span()`, `log()`, `addExporter()`, `currentTrace()`
- **Tracer:** `Tracer` class with `AsyncLocalStorage` context propagation; `ActiveTrace` and `SpanContext` helpers
- **Transport:** `postTrace()`, `postSpans()`, `flushBatch()` using native fetch
- **Cost:** `calculateCost(model, inputTokens, outputTokens)` — mirrors Python SDK pricing
- **Types:** `TracerConfig`, `SpanData`, `TracePayload`, `SpansPayload`, `LogEntry`, `CostData`, `SpanExporter`, `ISpanContext`
- **Build:** ESM + CJS dual output via tsup; TypeScript declarations included
- **Tests:** 30 vitest tests

#### Docker
- **Image:** `tranhoangtu/agentlens:0.4.0` (also tagged `latest`)

### Upgrade Instructions

**From v0.3.0 to v0.4.0:**

1. **Docker Image Update**
   ```bash
   docker pull tranhoangtu/agentlens:0.4.0
   docker run -p 3000:3000 tranhoangtu/agentlens:0.4.0
   ```

2. **Python SDK** — no change needed (already at v0.3.0)

3. **TypeScript SDK (new)**
   ```bash
   npm install agentlens-observe@0.1.0
   ```
   ```ts
   import * as agentlens from "agentlens-observe";
   agentlens.configure({ serverUrl: "http://localhost:3000" });
   const result = await agentlens.trace("MyAgent", async () => {
     const s = agentlens.span("llm_call", "llm_call").enter();
     s.setOutput("done");
     s.exit();
     return "done";
   });
   ```

4. **API Compatibility** — All v0.3.0 endpoints unchanged

---

## [0.3.0] — 2026-02-28

**Version:** 0.3.0 | **Status:** Maintained | **Release Type:** Major Feature Release

### Added

#### Replay / Time-Travel Debugging
- **Route:** `#/traces/:id/replay` — client-side only, zero backend changes
- **Hook:** `use-replay-controls.ts` — cursor, play/pause, speed 1–10x, step prev/next
- **Components:** `replay-transport-controls.tsx`, `replay-timeline-scrubber.tsx` (Gantt bars + range slider)
- **Page:** `trace-replay-page.tsx`; "Enter Replay" button added to trace detail page

#### OTel OTLP HTTP Ingestion
- **Endpoint:** `POST /api/otel/v1/traces` — accepts OTLP HTTP JSON (no protobuf/gRPC)
- **Mapper:** `server/otel_mapper.py` — pure function mapping OTel spans → AgentLens format
- **Kind mapping:** SERVER→agent_run, CLIENT→tool_call, INTERNAL→llm_call, default→task
- **agent_name** from `resource.attributes["service.name"]`, fallback `"otel"`
- **Tests:** 8 tests (4 unit mapper + 4 integration endpoint)

#### Server Tests
- Total server tests: 46 (up from 38)

---

## [0.2.0] — 2025-02-28

**Version:** 0.2.0 | **Status:** Production | **Release Type:** Major Feature Release

### Added

#### Dashboard UX Overhaul
- **shadcn/ui Design System** — Complete redesign with Radix UI primitives
- **9 UI Primitives** — badge, button, card, input, skeleton, table, separator, tooltip, scroll-area
- **Sidebar Navigation** — Fixed sidebar with trace/agent quick access
- **Dark Theme** — CSS variables-based dark mode (slate + blue color palette)
- **Responsive Layout** — Mobile-optimized dashboard

#### Search, Filters & Pagination
- **Full-Text Search** — Search agent_name via `q` query parameter
- **Status Filter** — running, completed, error
- **Agent Name Filter** — Dropdown of distinct agents
- **Date Range Filter** — ISO 8601 date picker (from_date, to_date)
- **Cost Range Filter** — Min/max cost slider
- **Sortable Columns** — Click column header to sort
- **Pagination Controls** — Limit selector (10, 25, 50, 100) + prev/next

#### Real-Time Improvements
- **Incremental Span Ingestion** — `POST /api/traces/{id}/spans` endpoint
- **Server-Sent Events (SSE)** — Real-time trace updates
- **span_created Events** — Per-span updates for live topology
- **trace_updated Events** — Aggregate trace metrics
- **Pulse Animation** — Running spans pulse 2s cycle
- **Live Trace Detail** — Real-time node updates while viewing

#### Trace Comparison Diff
- **Comparison Endpoint** — `GET /api/traces/compare?left=id1&right=id2`
- **LCS Algorithm** — Longest common subsequence matching
- **Side-by-Side Topologies** — React Flow dual graphs
- **Color-Coded Matching** — Green (match), red (deletion), blue (insertion)
- **Line Diff Panel** — Detailed span-by-span differences
- **Compare Route** — `#/compare/:left/:right`

#### SDK v0.2.0
- **27 LLM Models** — Pricing for GPT-4.1, Claude 4, Gemini 2.0, DeepSeek, Llama 3.3, and more
- **Batch Transport** — Queue with configurable batch_size (default 50) and batch_interval (default 5s)
- **Auto-Flush** — Automatic flush on timer or queue full
- **OpenTelemetry Exporter** — Bridge spans to OTel backends
- **Custom Logging** — `agentlens.log()` for metadata enrichment

#### Framework Integrations
- **LangChain** — AgentLensCallbackHandler for LangChain/LangGraph
- **CrewAI** — `patch_crewai()` auto-instrumentation
- **AutoGen** — `patch_autogen()` for ConversableAgent
- **LlamaIndex** — AgentLensCallbackHandler for LlamaIndex
- **Google ADK** — `patch_google_adk()` for Agent.run()

#### Testing Suite
- **38 Server Tests** — API endpoints, SSE, storage CRUD
- **52 SDK Tests** — Tracer, transport, pricing calculations
- **>82% Coverage** — pytest + httpx + respx
- **CI/CD Integration** — GitHub Actions validation

#### Performance Optimizations
- **Compound Indexes** — DB indexes on (status, created_at), (agent_name, created_at), (total_cost_usd)
- **GZip Compression** — Automatic JSON compression for >1KB responses
- **Code Splitting** — 4 chunks (index 282KB, recharts 335KB, react-flow 232KB, compare 14KB)
- **Virtualized Table** — @tanstack/react-virtual for 1000+ row tables
- **React.memo** — Memoization on expensive components
- **Lazy Compare** — Defer compare page load

### Changed

#### API Updates
- **GET /api/traces** — Enhanced filtering, sorting, pagination
  - New parameters: `q`, `status`, `agent_name`, `from_date`, `to_date`, `min_cost`, `max_cost`, `sort`, `order`, `limit`, `offset`
  - Response: `{traces, total, limit, offset}`
- **POST /api/traces/{id}/spans** — New endpoint for incremental ingestion
  - Publishes SSE events for each span
- **GET /api/traces/compare** — New comparison endpoint
  - Parameters: `left`, `right` trace IDs
  - Returns diff with matches, insertions, deletions

#### Database Schema
- **Trace Table** — Added compound indexes for filtering
- **Span Table** — Maintained for hierarchical traces
- **Index Strategy** — (status, created_at), (agent_name, created_at), (total_cost_usd)

#### SDK API
- **Tracer.configure()** — Added `batch_size`, `batch_interval` parameters
- **Tracer.add_exporter()** — New method for exporter attachment
- **Tracer.log()** — New method for custom logging
- **cost.py** — Expanded pricing table from 5 to 27 models

### Fixed

- **Concurrent Trace Ingestion** — Fixed race condition in span tree traversal
- **Empty Cost Calculations** — Handle null cost fields gracefully
- **SSE Reconnection** — Automatic reconnect on connection loss
- **Date Filter Validation** — Proper ISO 8601 parsing with error messages
- **Table Rendering** — Fixed virtualized table scroll performance
- **Dark Mode Toggle** — Persistent theme storage

### Removed

- **Old Dashboard UI** — Replaced with shadcn/ui (0.1.x dashboard deprecated)
- **Basic Topology** — Replaced with interactive React Flow
- **CSV Export** — (Planned for v0.3.0)

### Security

- **CORS Enabled** — All origins for dev, restrict in production
- **Input Validation** — Pydantic schemas for all requests
- **SQL Injection Protection** — SQLModel parameterized queries
- **Error Handling** — No sensitive data in error messages

### Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Trace Listing P50** | 150ms | With filters, 50 rows |
| **Compare Page Load** | 280ms | 100 spans each trace |
| **Topology Render** | 300ms | React Flow + 50 nodes |
| **Bundle Size** | 848KB → 4 chunks | 282KB + 335KB + 232KB + 14KB |
| **Database Writes** | <100ms | Per trace |
| **API Response** | GZip 40% reduction | On JSON >1KB |

### Dependencies Added

**Frontend:**
- `react`: 19.0.0
- `vite`: 7.0.0
- `tailwindcss`: 3.4.0
- `@radix-ui/primitive`: 1.0.0
- `react-flow-renderer`: 12.0.0
- `recharts`: 3.0.0
- `@tanstack/react-virtual`: 3.0.0

**Backend:**
- `fastapi`: 0.100.0
- `sqlmodel`: 0.0.14
- `pydantic`: 2.0.0

**SDK:**
- `httpx`: 0.25.0
- `pydantic`: 2.0.0

**Testing:**
- `pytest`: 7.4.0
- `httpx`: 0.25.0 (testing)
- `respx`: 0.20.0

### Upgrade Instructions

**From v0.1.0 to v0.2.0:**

1. **Docker Image Update**
   ```bash
   docker pull tranhoangtu/agentlens:0.2.0
   docker run -p 3000:3000 tranhoangtu/agentlens:0.2.0
   ```

2. **SDK Update**
   ```bash
   pip install --upgrade agentlens-observe==0.2.0
   ```

3. **API Compatibility** — All v0.1.0 endpoints supported
   - POST /api/traces ✅ (unchanged)
   - GET /api/traces/{id} ✅ (unchanged)
   - GET /api/traces ✅ (enhanced with filters)
   - POST /api/traces/{id}/spans ✅ (new)
   - GET /api/traces/compare ✅ (new)

4. **Data Migration** — None required (backward compatible)

### Known Issues

- SQLite write contention at >100 concurrent SDK clients (upgrade to PostgreSQL planned for v0.3.0)
- OTel integration one-way only (ingestion planned for v0.3.0)
- No user authentication (multi-tenant auth planned for v0.3.0)

---

## [0.1.0] — 2025-01-15

**Version:** 0.1.0 | **Status:** MVP | **Release Type:** Initial Release

### Added

#### Core Functionality
- **Trace Ingestion** — `POST /api/traces` endpoint
- **Trace Listing** — `GET /api/traces` with basic filtering
- **Trace Details** — `GET /api/traces/{id}` with span hierarchy
- **Topology Visualization** — Basic React Flow rendering
- **Python SDK** — Decorator-based instrumentation
- **Docker Support** — Single-stage containerization
- **PyPI Distribution** — `pip install agentlens-observe`

#### Features
- **Span Hierarchy** — Parent-child span relationships
- **Status Tracking** — running, completed, error states
- **Cost Tracking** — Basic pricing for 5 LLM models
- **SQLite Backend** — Lightweight, file-based persistence
- **Manual Instrumentation** — Full control over span creation

#### Testing
- **Unit Tests** — Basic storage and API tests
- **Integration Tests** — End-to-end trace ingestion

### Performance

| Metric | Value |
|--------|-------|
| **Bundle Size** | 1.2MB (unoptimized) |
| **Trace Listing P50** | 200ms |
| **API Response** | 50-100ms |

### Known Limitations

- No real-time updates (polling only)
- Basic UI (no dark mode, minimal components)
- No trace comparison
- No search/filters
- SQLite only (single-machine)
- Limited framework integrations

---

## Version Naming Convention

**Format:** MAJOR.MINOR.PATCH

- **MAJOR** (0.x.0) — Breaking API changes, major features
- **MINOR** (x.1.0) — New features, backward compatible
- **PATCH** (x.x.1) — Bug fixes, performance tuning

**Stability Tiers:**
- `0.x.x` — Beta (breaking changes possible)
- `1.0.0+` — Stable (semantic versioning)

---

## Support & Deprecation

### Supported Versions

| Version | Status | Support Until |
|---------|--------|---------------|
| 0.4.0 | Current | 0.5.0 release |
| 0.3.0 | Maintained | 6 months |
| 0.2.0 | EOL | 2026-02-28 |
| 0.1.0 | EOL | 2025-02-28 |

### Deprecation Policy

- 6-month notice before removal
- Documented migration path
- Extended support for critical security issues

---

## Changelog Format

All changes follow this format:

```markdown
### [Category]

- **Feature Name** — Description with impact
```

**Categories:**
- Added — New features
- Changed — API/behavior changes
- Deprecated — Future removal warnings
- Removed — Deleted features
- Fixed — Bug fixes
- Security — Security updates
- Performance — Optimization improvements

---

## Contributing to Changelog

1. Create PR with changes
2. Update CHANGELOG.md in PR
3. Use present tense ("Add feature" not "Added feature")
4. Reference GitHub issues (#123)
5. Include impact/rationale

---

## Release Schedule

- **Patch releases:** As needed (bug fixes)
- **Minor releases:** Quarterly (new features)
- **Major releases:** Annually (strategic changes)

**Next Planned Release:** v0.5.0
- PostgreSQL backend
- Alerting framework
- TypeScript SDK framework integrations (LangChain.js, LlamaIndex.js)
