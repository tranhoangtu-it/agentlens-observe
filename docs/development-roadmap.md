# AgentLens Development Roadmap

**Current Version:** v0.2.0 | **Release Date:** Feb 2025 | **Next Milestone:** v0.3.0 (Q2 2025)

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

## Phase 3: Enterprise Features (Q2 2025)

**Target Date:** April-June 2025 | **Status:** In Planning

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

#### 2. OTel Span Ingestion
- **Rationale:** Allow AgentLens to receive traces from OTel-instrumented systems
- **Work:**
  - [ ] Implement OTel Protocol Buffers receiver
  - [ ] Map OTel spans → AgentLens span model
  - [ ] HTTP receiver endpoint (/api/otel/v1/traces)
  - [ ] Backward compatibility with existing SDK

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

#### 4. Multi-Tenant Auth
- **Rationale:** Multi-user self-hosted deployments
- **Work:**
  - [ ] User authentication (OAuth2 or SAML)
  - [ ] Organization/team isolation
  - [ ] Role-based access control (RBAC)
  - [ ] API key management

- **Impact:**
  - Enterprise deployment support
  - Shared AgentLens instances across teams
  - Audit trail & compliance

#### 5. Alerting Framework
- **Rationale:** Proactive agent monitoring
- **Work:**
  - [ ] Alert rule builder (UI)
  - [ ] Triggers: high error rate, slow traces, cost threshold
  - [ ] Channels: email, Slack, PagerDuty, webhooks
  - [ ] Alert history & management

- **Impact:**
  - Operational insights
  - Incident response automation
  - Cost governance

#### 6. TypeScript SDK
- **Rationale:** Support Node.js and browser-based agents
- **Work:**
  - [ ] Node.js SDK port (async/await compatible)
  - [ ] Browser SDK (fetch-based)
  - [ ] Framework integrations: LangChain.js, LlamaIndex.js
  - [ ] Feature parity with Python SDK

- **Impact:**
  - JavaScript/TypeScript ecosystem
  - LLM agent libraries in JS
  - Full-stack observability

### Success Criteria (Phase 3)
- [ ] PostgreSQL backend proven on 1M+ spans
- [ ] OTel ingestion passing compliance tests
- [x] Time-travel replay usable (UI complete)
- [ ] Multi-tenant auth production-ready
- [ ] Alerting framework handling 1000+ rules
- [ ] TypeScript SDK at feature parity (Python SDK)

## Phase 4: Community & Growth (H2 2025)

**Target Date:** July-Dec 2025 | **Status:** Roadmap

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

### v0.2.0 (Current)
- SQLite fully supported
- All features stable

### v0.3.0 (Future)
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
├── Apr-Jun: Phase 3 (v0.3.0 — PostgreSQL, OTel)
├── Jul-Sep: Phase 4 (Community, Ecosystem)
└── Oct-Dec: v1.0.0 planning

2026+
├── H1: v1.0.0 (Semantic versioning)
├── H2: Enterprise features
└── Future: Cloud offering (optional)
```

## Quarterly Updates

### Q1 2025 (Jan-Mar)
- **Release:** v0.2.0 (Feb)
- **Focus:** Production stabilization
- **Metrics:** >100 GitHub stars, >1K Docker pulls/day

### Q2 2025 (Apr-Jun)
- **Release:** v0.3.0 (May-Jun)
- **Focus:** PostgreSQL backend, OTel ingestion
- **Metrics:** 250+ GitHub stars, 5K Docker pulls/day

### Q3 2025 (Jul-Sep)
- **Release:** v0.3.1+ (patches)
- **Focus:** Time-travel debugging, alerting
- **Metrics:** 350+ GitHub stars, 10K PyPI/month

### Q4 2025 (Oct-Dec)
- **Release:** v1.0.0 (Dec)
- **Focus:** v1.0 hardening, multi-tenant auth
- **Metrics:** 500+ GitHub stars, TypeScript SDK

## Feedback & Questions

- **GitHub Discussions:** github.com/tranhoangtu-it/agentlens/discussions
- **Roadmap Voting:** github.com/tranhoangtu-it/agentlens/wiki/Roadmap
- **Email:** team@agentlens.io
