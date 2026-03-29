# AgentLens Changelog

All notable changes documented. Format follows [Keep a Changelog](https://keepachangelog.com/).

## [0.7.0] — 2026-03-29

**Version:** 0.7.0 | **Status:** Production | **Release Type:** Feature Release

### Added

#### LLM Settings & Encryption
- **GET/PUT /api/settings** — User LLM configuration endpoints
- **Supported Providers:** OpenAI, Anthropic, Google, Custom (extensible)
- **Encrypted Storage** — API keys encrypted with cryptography.Fernet (never stored plain)
- **Per-User Isolation** — Each user has separate LLM settings
- **Dashboard Settings Page** — UI for configuring LLM provider and model

#### AI Failure Autopsy
- **POST /api/traces/{id}/autopsy** — Request AI analysis of failed traces
- **GET /api/traces/{id}/autopsy** — Retrieve cached analysis results
- **DELETE /api/traces/{id}/autopsy** — Remove autopsy analysis
- **AI-Powered Analysis** — Uses user's configured LLM provider to analyze failure
- **Recommendations** — AI generates root cause and remediation suggestions
- **Dashboard Autopsy Panel** — Integrated into trace detail page

#### MCP Protocol Integration
- **Python: `agentlens.integrations.mcp.patch_mcp()`** — Auto-instrument MCP servers
- **TypeScript: `patchMcp()`** from `agentlens/integrations/mcp` — MCP client tracing
- **New Span Types:** `mcp.tool_call`, `mcp.resource_read`, `mcp.prompt_get`
- **Optional Dependency** — `pip install agentlens[mcp]` for MCP features

#### Server Modules
- **`crypto.py`** — Fernet encryption/decryption for secure credential storage
- **`settings_models.py`, `settings_storage.py`** — User LLM settings CRUD with encryption
- **`llm_provider.py`** — Abstract LLM provider interface; OpenAI, Anthropic, Google impls
- **`autopsy_models.py`, `autopsy_storage.py`, `autopsy_analyzer.py`** — Failure analysis system

### Changed
- Span type enum expanded to include MCP operation types
- Database schema: added UserSettings and Autopsy tables
- FastAPI main.py: added settings and autopsy route handlers

### Dependencies
- **Added:** `cryptography>=42.0` for credential encryption
- **Optional:** `mcp>=0.8.0` (only when installing with `[mcp]` extra)

### Upgrade Instructions

**From v0.6.0 to v0.7.0:**

1. **Docker Image Update**
   ```bash
   docker pull tranhoangtu/agentlens-observe:0.7.0
   docker run -p 3000:3000 -e AGENTLENS_JWT_SECRET=your-secret tranhoangtu/agentlens-observe:0.7.0
   ```

2. **SDK Update**
   ```bash
   # Python
   pip install --upgrade agentlens-observe==0.7.0

   # For MCP integration
   pip install agentlens-observe[mcp]==0.7.0

   # TypeScript
   npm install agentlens-observe@0.7.0
   ```

3. **New Features (Optional)**
   - Configure LLM settings via dashboard Settings page
   - Enable AI Autopsy by setting up LLM provider
   - Instrument MCP servers with patch_mcp() / patchMcp()

4. **API Compatibility** — All v0.6.0 endpoints unchanged; new endpoints are additive

---

## [0.6.0] — 2026-03-01

**Version:** 0.6.0 | **Status:** Production | **Release Type:** Quality & Infrastructure Release

### Added

#### Test Coverage Expansion
- **231 total tests** (86 server + 52 Python SDK + 30 TypeScript SDK + 63 integration)
- **100% production code coverage** — all non-test code paths covered
- **New integration tests** — end-to-end workflows, framework combinations
- **Comprehensive suite** — pytest + httpx + respx + vitest

#### Security Hardening
- **CORS Environment Config** — Configurable via `AGENTLENS_CORS_ORIGINS` (lockdown production, open dev)
- **JWT Secret Warning** — Startup warning if AGENTLENS_JWT_SECRET default used
- **Webhook SSRF Protection** — Block private IP ranges (10.0.0.0/8, 127.0.0.0/8, 172.16.0.0/12) to prevent SSRF attacks
- **Security Badges** — Added to GitHub profile

#### Documentation Site
- **18-page Astro + Starlight documentation** — https://agentlens-observe.pages.dev
- **Content:** Getting started, API reference, SDK guides, integrations, CLI, troubleshooting, FAQ, contributing
- **Deployment:** Cloudflare Pages with automatic builds
- **SEO:** Sitemap, structured data, OpenGraph metadata

#### GitHub Improvements
- **6 repository badges** — Latest release, Docker pulls, npm downloads, tests passing, coverage, license
- **Issue templates** — Bug report, feature request, security vulnerability
- **Repository topics** — ai-agents, observability, llm, open-source
- **Release notes** — Automated via GitHub release

### Changed
- Docker image renamed: `tranhoangtu/agentlens:0.5.0` → `tranhoangtu/agentlens-observe:0.6.0`
- All 0.5.0 references updated to 0.6.0 in docs, Docker, PyPI, npm

### Fixed
- CORS configuration allows production lockdown (was all-origins only)
- Webhook security: no external network exposure, SSRF-protected
- JWT secret auto-generation warning (encourages env config)

### Performance
- Test suite execution time optimized
- No performance regressions from coverage improvements

### Upgrade Instructions

**From v0.5.0 to v0.6.0:**

1. **Docker Image Update**
   ```bash
   docker pull tranhoangtu/agentlens-observe:0.6.0
   docker run -p 3000:3000 -e AGENTLENS_JWT_SECRET=your-secret tranhoangtu/agentlens-observe:0.6.0
   ```

2. **CORS Configuration (Production)**
   ```bash
   # Lock down CORS for production
   docker run -p 3000:3000 \
     -e AGENTLENS_JWT_SECRET=your-secret \
     -e AGENTLENS_CORS_ORIGINS="https://yourdomain.com" \
     tranhoangtu/agentlens-observe:0.6.0
   ```

3. **SDK Compatibility** — No changes needed (backward compatible)

4. **API Compatibility** — All v0.5.0 endpoints unchanged

---

## [0.5.0] — 2026-02-28

**Version:** 0.5.0 | **Status:** Production | **Release Type:** Major Feature Release

### Added

#### Multi-Tenant Authentication
- **User Registration** — `POST /api/auth/register` (email, password, display_name)
- **JWT Login** — `POST /api/auth/login` (HS256, 24h expiry, Bearer token)
- **API Key Auth** — Create/list/delete API keys (`al_` prefix, SHA-256 hashed)
- **Per-User Isolation** — Traces, alert rules, alert events scoped by user_id
- **Dashboard Auth UI** — Login page, AuthProvider context, protected routes
- **SSE Per-User Filtering** — Events only sent to owning user
- **Orphan Data Migration** — Existing data auto-assigned to admin user on startup
- **Cross-Tenant Protection** — 404 (not 403) for other users' resources

#### Alerting Framework
- **Alert Rules CRUD** — `POST/GET/PUT/DELETE /api/alert-rules`
- **Metrics:** cost, latency, error_rate with gt/lt/gte/lte operators
- **Evaluation on Ingestion** — Rules checked automatically when traces arrive
- **Alert Events** — `GET /api/alerts`, `PATCH /api/alerts/{id}/resolve`, `GET /api/alerts/summary`
- **Wildcard Rules** — `agent_name="*"` matches any agent
- **Dashboard Pages** — Alert rules list, alert events list

#### Server Auth Files
- `auth_models.py` — User + ApiKey SQLModel tables
- `auth_storage.py` — CRUD with bcrypt + SHA-256
- `auth_jwt.py` — JWT encode/decode (PyJWT)
- `auth_deps.py` — FastAPI dependency for get_current_user
- `auth_routes.py` — Auth API endpoints
- `auth_seed.py` — Admin seeder + orphan data migration

#### Testing
- **86 server tests** (up from 46)
- **27 new auth/isolation tests** — register, login, me, API keys, tenant isolation
- **86% code coverage**

### Changed
- All data endpoints now require authentication (Bearer token or X-API-Key)
- Health endpoint (`GET /api/health`) remains public
- SSE bus rewritten with per-user subscriber filtering
- `user_id` column added to Trace, AlertRule, AlertEvent tables

### Security
- bcrypt password hashing (12 rounds)
- SHA-256 API key hashing (raw key never stored)
- JWT HS256 with configurable secret (AGENTLENS_JWT_SECRET env)
- Cross-tenant access returns 404 to prevent enumeration
- Default admin password warning on startup

### Upgrade Instructions

**From v0.4.0 to v0.5.0:**

1. **Docker Image Update**
   ```bash
   docker pull tranhoangtu/agentlens-observe:0.5.0
   docker run -p 3000:3000 -e AGENTLENS_JWT_SECRET=your-secret tranhoangtu/agentlens-observe:0.5.0
   ```

2. **First Run** — Admin user auto-created (admin@agentlens.local / changeme)
3. **Change Admin Password** — Login and update immediately
4. **SDK Update** — Add API key header:
   ```python
   agentlens.configure(server_url="http://localhost:3000", api_key="al_...")
   ```
5. **Breaking Change** — All data endpoints now require auth. SDK clients must provide API key.

---

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
- **Image:** `tranhoangtu/agentlens-observe:0.4.0` (also tagged `latest`)

### Upgrade Instructions

**From v0.3.0 to v0.4.0:**

1. **Docker Image Update**
   ```bash
   docker pull tranhoangtu/agentlens-observe:0.4.0
   docker run -p 3000:3000 tranhoangtu/agentlens-observe:0.4.0
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
   docker pull tranhoangtu/agentlens-observe:0.2.0
   docker run -p 3000:3000 tranhoangtu/agentlens-observe:0.2.0
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
| 0.6.0 | Current | 0.7.0 release |
| 0.5.0 | Maintained | 6 months |
| 0.4.0 | EOL | 2026-03-01 |
| 0.3.0 | EOL | 2026-02-28 |
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

**Next Planned Release:** v0.7.0 (2026-Q2)
- PostgreSQL backend (multi-instance scaling)
- RBAC (role-based access control, org-level scoping)
- TypeScript SDK framework integrations (LangChain.js, LlamaIndex.js)
