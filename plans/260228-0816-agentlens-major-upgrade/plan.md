---
title: "AgentLens Major Upgrade: MVP to Production-Ready"
description: "Comprehensive upgrade plan: dashboard UX overhaul, trace comparison, real-time improvements, SDK expansion, testing, and performance optimization"
status: pending
priority: P1
effort: 40h
branch: feat/major-upgrade-v0.2
tags: [dashboard, ux, sdk, testing, performance, open-source]
created: 2026-02-28
---

# AgentLens Major Upgrade Plan

## Current State

- **Codebase**: 1,513 LOC across 21 source files (dashboard: 732, server: 314, sdk: 467)
- **Stack**: React 19 + Vite 7 + React Flow 12 + Tailwind 3 + Recharts 3 | FastAPI + SQLite/SQLModel | Python SDK + httpx
- **Architecture**: Monolith Docker container (static SPA + FastAPI), SSE for real-time, fire-and-forget SDK transport
- **Limitations**: No search/filter, no auth, no tests, no pagination, no trace comparison, no OTel, basic UI

## Upgrade Strategy

**Principle**: Maximize visual impact first (GitHub stars), then depth (power users), then robustness (production).

Phases are ordered by **star-attracting impact** and can be parallelized where noted.

## Phases

| # | Phase | Status | Effort | Parallel Group |
|---|-------|--------|--------|----------------|
| 1 | [Dashboard UX Overhaul](phase-01-dashboard-ux-overhaul.md) | **completed** | 12h | A |
| 2 | [Search, Filters & Pagination](phase-02-search-filters-pagination.md) | **completed** | 6h | A |
| 3 | [Real-Time Improvements](phase-03-realtime-improvements.md) | **completed** | 5h | A |
| 4 | [Trace Comparison / Diff](phase-04-trace-comparison-diff.md) | **completed** | 6h | B (after P1) |
| 5 | [SDK Improvements & Integrations](phase-05-sdk-improvements.md) | **completed** | 5h | B |
| 6 | [Testing Suite](phase-06-testing-suite.md) | **completed** | 4h | C (after P1-P5) |
| 7 | [Performance & Scale](phase-07-performance-and-scale.md) | **completed** | 2h | C |

## Parallel Execution Map

```
Group A (can run in parallel):       Group B (after Phase 1):        Group C (after all):
  Phase 1 (Dashboard UX)              Phase 4 (Trace Diff)           Phase 6 (Tests)
  Phase 2 (Search/Filter)             Phase 5 (SDK)                  Phase 7 (Performance)
  Phase 3 (Real-time)
```

## File Ownership Boundaries

| Owner | Files |
|-------|-------|
| Dashboard Dev 1 | `dashboard/src/components/*`, `dashboard/src/lib/*`, `dashboard/tailwind.config.js`, `dashboard/package.json` |
| Dashboard Dev 2 | `dashboard/src/pages/*`, `dashboard/src/App.tsx` |
| Server Dev | `server/*` |
| SDK Dev | `sdk/*` |
| Tester | `server/tests/*`, `sdk/tests/*`, `dashboard/src/__tests__/*` |

## Key Dependencies

- Phase 1 (UX) should land first: all other dashboard phases build on new component library
- Phase 2 (Search) requires server API changes that Phase 4 (Diff) also depends on
- Phase 5 (SDK) is fully independent of dashboard work
- Phase 6 (Tests) tests the final code after all features land

## New Dependencies to Add

| Layer | Package | Purpose |
|-------|---------|---------|
| Dashboard | `tailwind-merge`, `clsx`, `class-variance-authority` | shadcn/ui style utility classes |
| Dashboard | `@radix-ui/react-dialog`, `@radix-ui/react-popover`, `@radix-ui/react-select` | Accessible UI primitives |
| Dashboard | `lucide-react` | Icon library (shadcn standard) |
| Dashboard | `date-fns` | Date formatting/range |
| Dashboard | `cmdk` | Command palette (optional, Phase 2) |
| Server | `pytest`, `pytest-asyncio`, `httpx` (test) | Testing |
| SDK | `pytest`, `respx` | SDK testing |
| SDK | `opentelemetry-api` (optional) | OTel export |

## Success Criteria

1. Dashboard looks professional (shadcn/ui dark theme, consistent spacing, animations)
2. Users can search/filter/paginate traces
3. Live topology graph updates as spans stream in
4. Side-by-side trace diff works for any two traces
5. SDK supports OTel export + AutoGen/LlamaIndex/ADK integrations
6. >80% test coverage on server + SDK
7. Handles 10K+ traces without UI lag
