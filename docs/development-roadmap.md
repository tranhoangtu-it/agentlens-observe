# AgentLens Development Roadmap

**Current Version:** v0.6.0 | **Release Date:** Mar 2026 | **Status:** Feature-Complete Milestone

## Phase 1: MVP (COMPLETED ✅)

**Timeframe:** Oct 2024 - Jan 2025 | **Status:** Shipped

### Completed Features
- [x] Basic trace ingestion (POST /api/traces)
- [x] Simple trace listing (GET /api/traces)
- [x] Trace detail view with basic topology
- [x] Python SDK with decorator-based instrumentation
- [x] Docker containerization
- [x] PyPI distribution

### Metrics Achieved
- 38K lines of code
- Single-page React dashboard
- SQLite backend (MVP-grade)

## Phase 2: Production-Ready (COMPLETED ✅)

**Timeframe:** Feb 2025 | **Status:** Shipped (v0.2.0)

### Completed Features

#### 1. Dashboard UX Overhaul ✅
- [x] shadcn/ui design system + Radix UI primitives
- [x] Sidebar navigation layout
- [x] CSS variables dark theme
- [x] 9 UI primitives (badge, button, card, input, skeleton, table, separator, tooltip, scroll-area)
- [x] Responsive mobile layout

#### 2. Search, Filters & Pagination ✅
- [x] Full-text search on agent_name (q parameter)
- [x] Status filter (running|completed|error)
- [x] Agent name filter
- [x] Date range filter (from_date, to_date)
- [x] Cost range filter (min_cost, max_cost)
- [x] Sortable columns (created_at, status, cost, span_count)
- [x] Pagination with configurable page size (10, 25, 50, 100)

#### 3. Real-Time Improvements ✅
- [x] Incremental span ingestion (POST /api/traces/{id}/spans)
- [x] Server-Sent Events (SSE) for live updates
- [x] span_created events (per new span)
- [x] trace_updated events (aggregate updates)
- [x] Pulse animation on running nodes
- [x] Real-time trace detail page

#### 4. Trace Comparison Diff ✅
- [x] Server-side LCS span tree diff algorithm
- [x] GET /api/traces/compare endpoint
- [x] Side-by-side React Flow topology graphs
- [x] Color-coded matching (green=match, red=delete, blue=insert)
- [x] Line diff view (LCS line-by-line diff)
- [x] Route: #/compare/:left/:right

#### 5. SDK v0.2.0 Improvements ✅
- [x] 27 LLM model pricing (GPT-4.1, Claude 4, Gemini 2.0, DeepSeek, Llama 3.3, etc.)
- [x] Batch transport with configurable auto-flush
- [x] OpenTelemetry span exporter bridge
- [x] agentlens.log() for custom logging
- [x] Framework integrations: LangChain, CrewAI, AutoGen, LlamaIndex, Google ADK

#### 6. Testing Suite ✅
- [x] 38 server tests (FastAPI endpoints, SSE, storage)
- [x] 52 SDK tests (tracer, transport, cost)
- [x] >82% code coverage
- [x] pytest + httpx + respx test stack

#### 7. Performance & Scale ✅
- [x] Compound database indexes (status+created_at, agent_name+created_at, total_cost_usd)
- [x] GZip middleware for JSON compression
- [x] Code splitting (4 chunks: 282KB index, 335KB recharts, 232KB react-flow, 14KB compare)
- [x] @tanstack/react-virtual virtualized table (1000+ rows)
- [x] React.memo on expensive components
- [x] Lazy-loaded compare page

### Metrics Achieved
- 410K tokens (codebase)
- 104 files (source + assets)
- 90+ tests, >82% coverage
- 4 chunks (optimal code splitting)
- <200ms P50 trace listing
- <300ms P50 compare page load

## Phase 3: Quality & Infrastructure (COMPLETED ✅)

**Target Date:** Mar 2026 | **Status:** Shipped (v0.6.0)

### Completed Features

#### Test Coverage & Quality
- [x] 231 total tests (100% prod coverage)
- [x] Integration test suite (63 tests)
- [x] All frameworks tested (LangChain, CrewAI, AutoGen, LlamaIndex, Google ADK)
- [x] CI/CD validation passing

#### Security Hardening
- [x] CORS environment configuration (production lockdown)
- [x] JWT secret startup warning
- [x] Webhook SSRF protection (block private IPs)
- [x] Security badges on GitHub

#### Documentation Site
- [x] 18-page Astro + Starlight site (agentlens-observe.pages.dev)
- [x] Automatic deployment via Cloudflare Pages
- [x] Comprehensive guides (getting started, API, SDK, integrations, troubleshooting)
- [x] SEO optimization (sitemap, structured data, OpenGraph)

#### GitHub Improvements
- [x] 6 repository badges (release, Docker, npm, tests, coverage, license)
- [x] Issue templates (bug, feature, security)
- [x] Repository topics and metadata
- [x] Automated release notes

### Success Criteria (Phase 3)
- [x] 100% production code coverage
- [x] 231 tests passing, zero flaky tests
- [x] Security hardening complete
- [x] Documentation site live and indexed
- [x] GitHub project fully professionalized

---

## Phase 4: LLM Settings & Autopsy (Q1 2026)

**Target Date:** March 2026 | **Status:** Shipped (v0.7.0)

### Completed Features

#### 1. User LLM Settings ✅
- [x] GET/PUT /api/settings endpoints
- [x] Support for OpenAI, Anthropic, Google, Custom providers
- [x] Encrypted credential storage (cryptography>=42.0)
- [x] Per-user API key isolation
- [x] Dashboard settings page

#### 2. AI Failure Autopsy ✅
- [x] POST/GET/DELETE /api/traces/{id}/autopsy endpoints
- [x] AI-powered trace failure analysis
- [x] Root cause identification
- [x] Actionable recommendations
- [x] Dashboard autopsy panel on trace detail

#### 3. MCP Protocol Integration ✅
- [x] Python: patch_mcp() for MCP server tracing
- [x] TypeScript: patchMcp() for MCP client tracing
- [x] New span types: mcp.tool_call, mcp.resource_read, mcp.prompt_get
- [x] Optional dependency: pip install agentlens[mcp]

#### 4. Server Modules ✅
- [x] crypto.py — Fernet encryption/decryption
- [x] settings_*.py — User settings CRUD + encryption
- [x] llm_provider.py — Provider abstraction + implementations
- [x] autopsy_*.py — Analysis system + storage

### Success Criteria (Phase 4)
- [x] Encrypted credential storage (no plaintext API keys in DB)
- [x] AI autopsy callable via API + usable in UI
- [x] MCP integration available for Python + TypeScript
- [x] Optional dependency architecture (not required for core)

---

## Phase 5: Enterprise Features (Q2 2026)

**Target Date:** April-June 2026 | **Status:** In Planning

### Features Under Consideration

#### 1. PostgreSQL Backend
- **Rationale:** SQLite bottleneck at >50K spans, need multi-instance scaling
- **Work:**
  - [ ] Migrate storage.py to SQLAlchemy + PostgreSQL
  - [ ] Add connection pooling (pgbouncer)
  - [ ] Implement database migrations (Alembic)
  - [ ] Performance testing vs SQLite

- **Impact:**
  - Multi-server deployments
  - Horizontal scaling
  - Full-text search optimization (PostgeSQL `tsvector`)
  - Transaction isolation levels

#### 2. OTel Span Ingestion ✅
- **Rationale:** Allow AgentLens to receive traces from OTel-instrumented systems
- **Work:**
  - [x] Map OTel spans → AgentLens span model (`server/otel_mapper.py`)
  - [x] HTTP receiver endpoint (`POST /api/otel/v1/traces`, OTLP HTTP JSON)
  - [x] Kind mapping: SERVER→agent_run, CLIENT→tool_call, INTERNAL→llm_call
  - [x] 8 tests (4 unit mapper + 4 integration)

- **Impact:**
  - OpenTelemetry ecosystem integration
  - Multi-platform observability
  - Unified agent + infrastructure traces

#### 3. Time-Travel Debugging (Replay) ✅
- **Rationale:** Allow users to step through agent execution
- **Work:**
  - [x] Record agent state at each span
  - [x] Implement trace stepping UI
  - [x] Rewind/fast-forward trace playback
  - [x] Variable inspector (state at each step)

- **Impact:**
  - Advanced debugging capabilities
  - Reduces debugging time 50%
  - Differentiator from competitors

#### 4. Multi-Tenant Auth ✅
- **Rationale:** Multi-user self-hosted deployments
- **Work:**
  - [x] User registration + JWT login (HS256, 24h expiry)
  - [x] API key auth (SHA-256 hashed, `al_` prefix, X-API-Key header)
  - [x] Per-user data isolation (traces, alert rules, alert events)
  - [x] API key management (create/list/delete)
  - [x] Dashboard auth UI (login page, auth context, protected routes)
  - [x] SSE per-user event filtering
  - [x] Orphan data migration (auto-assign to admin)
  - [x] 27 tests (auth + tenant isolation)

- **Impact:**
  - Enterprise deployment support
  - Shared AgentLens instances across teams
  - Secure per-user data isolation

#### 5. Alerting Framework ✅
- **Rationale:** Proactive agent monitoring
- **Work:**
  - [x] Alert rule CRUD API (POST/GET/PUT/DELETE /api/alert-rules)
  - [x] Evaluation on trace ingestion (cost, latency, error_rate metrics)
  - [x] Alert events API (list, resolve, summary)
  - [x] Wildcard rules (agent_name="*")
  - [x] Dashboard alert pages (rule list, event list)
  - [x] 14 alert tests

- **Impact:**
  - Operational insights
  - Cost governance
  - Proactive anomaly detection

#### 6. TypeScript SDK ✅
- **Rationale:** Support Node.js and browser-based agents
- **Work:**
  - [x] Node 18+ SDK (AsyncLocalStorage, native fetch, zero prod deps)
  - [x] Public API: `configure`, `trace`, `span`, `log`, `addExporter`, `currentTrace`
  - [x] ESM + CJS dual output via tsup
  - [x] 30 vitest tests
  - [x] Published to npm as `agentlens-observe@0.1.0`
  - [ ] Framework integrations: LangChain.js, LlamaIndex.js (future)

- **Impact:**
  - JavaScript/TypeScript ecosystem
  - LLM agent libraries in JS
  - Full-stack observability

### Success Criteria (Phase 3)
- [ ] PostgreSQL backend proven on 1M+ spans
- [x] OTel ingestion (OTLP HTTP JSON, 8 tests passing)
- [x] Time-travel replay usable (UI complete)
- [x] Multi-tenant auth production-ready (JWT + API key, 27 tests)
- [x] Alerting framework (cost/latency/error_rate, 14 tests)
- [x] TypeScript SDK v0.1.0 published to npm

## Phase 5: Community & Growth (H2 2026)

**Target Date:** July-Dec 2026 | **Status:** Roadmap

### Features
- [ ] Community plugin ecosystem
- [ ] Dashboard customization (custom pages, widgets)
- [ ] Export integrations (data warehousing, BI tools)
- [ ] Benchmarking suite (agent performance comparison)
- [ ] Marketplace for integrations

## Backlog (Future)

### Under Consideration
- **Redis caching layer** — Cache hot traces, filters
- **Agent clustering** — Group related traces, agent families
- **Cost analytics** — Trends, anomalies, forecasting
- **A/B testing framework** — Compare agent variants
- **Fine-tuning data export** — Export traces for model fine-tuning
- **Mobile app** — Native iOS/Android clients

## Deprecation Schedule

### v0.4.0 (Current)
- SQLite fully supported
- All features stable

### v0.5.0 (Future)
- SQLite marked for deprecation
- PostgreSQL recommended for new deployments
- 6-month migration window for existing users

### v1.0.0 (Future)
- SQLite removed
- PostgreSQL mandatory
- Semantic versioning enforced

## Success Metrics (Overall)

| Metric | Target | Current |
|--------|--------|---------|
| **GitHub Stars** | 500 | ~100 (Feb 2025) |
| **PyPI Downloads** | 10K/month | ~500/month (Feb 2025) |
| **Docker Pulls** | 50K/month | ~1K/month (Feb 2025) |
| **Test Coverage** | >90% | >82% ✅ |
| **Performance (P50)** | <200ms | 150ms ✅ |
| **Uptime** | 99.9% | 99.99% ✅ |

## Contributing to Roadmap

Community feedback shapes AgentLens roadmap. To contribute:

1. **Request a feature:** GitHub Issues with `[feature-request]` tag
2. **Vote on features:** React/emoji voting on issues
3. **Contribute code:** PRs welcome for any roadmap item
4. **Sponsor development:** Reach out for sponsorship opportunities

## Timeline Summary

```
2024
├── Oct-Nov: Phase 1 (MVP)
└── Dec-Jan: Phase 1 finalization

2025
├── Feb: Phase 2 (v0.2.0) ✅
├── Feb-Feb: Phase 2 continued (v0.3.0 — Replay, OTel) ✅
├── Feb-Feb: Phase 2 continued (v0.4.0 — TypeScript SDK) ✅
└── Feb-Feb: Phase 2 continued (v0.5.0 — Auth, Alerting) ✅

2026
├── Mar: Phase 3 (v0.6.0 — Quality, Infrastructure) ✅
├── Mar: Phase 4 (v0.7.0 — LLM Settings, Autopsy, MCP) ✅
├── Apr-Jun: Phase 5 (v0.8.0 — PostgreSQL, RBAC)
├── Jul-Sep: Phase 6 (Community, Ecosystem)
└── Oct-Dec: v1.0.0 planning

2026+
├── H1 2026: v1.0.0 (Semantic versioning)
├── H2 2026: Enterprise features
└── Future: Cloud offering (optional)
```

## Quarterly Updates

### Q1 2026 (Jan-Mar)
- **v0.6.0 (Mar)** — Test coverage, security hardening, documentation
  - Metrics: 100% prod coverage, 231 tests, 18-page docs site, 6 GitHub badges ✅
- **v0.7.0 (Mar)** — LLM Settings, Autopsy, MCP Integration
  - Metrics: Encrypted credentials, AI failure analysis, MCP tracing ✅

### Q2 2026 (Apr-Jun)
- **Release:** v0.8.0 (May-Jun)
- **Focus:** PostgreSQL backend, RBAC, multi-instance scaling
- **Metrics:** 500+ GitHub stars, PostgreSQL support, 10K PyPI/month

### Q3 2026 (Jul-Sep)
- **Release:** v0.9.0 (patches)
- **Focus:** Community ecosystem, marketplace, export integrations
- **Metrics:** 750+ GitHub stars, 50K PyPI/month, plugin ecosystem

### Q4 2026 (Oct-Dec)
- **Release:** v1.0.0 (Dec)
- **Focus:** Stable API, semantic versioning, enterprise support
- **Metrics:** 1000+ GitHub stars, production-grade stability

## Feedback & Questions

- **GitHub Discussions:** github.com/tranhoangtu-it/agentlens-observe/discussions
- **Roadmap Voting:** github.com/tranhoangtu-it/agentlens-observe/wiki/Roadmap
- **Documentation:** https://agentlens-observe.pages.dev
- **Email:** team@agentlens.io
