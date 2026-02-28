# Docs Update Report — v0.5.0 (Alerting + Auth)

**Date:** 2026-02-28 | **Scope:** v0.5.0 changes (commits fd45b67, 0434229)

## Files Updated

| File | LOC Before | LOC After | Changes |
|------|-----------|-----------|---------|
| `docs/system-architecture.md` | 326 | 434 | Major: auth + alerting sections |
| `docs/codebase-summary.md` | 249 | 255 | Major: rewrote server section, updated stats |
| `docs/project-overview-pdr.md` | 169 | 195 | Added F8 (auth), F9 (alerting), updated roadmap |
| `docs/development-roadmap.md` | 292 | 292 | Already up to date — verified, no changes |
| `docs/project-changelog.md` | 447 | 447 | Already up to date — verified, no changes |

All files under 800 LOC limit.

## Changes Made

### system-architecture.md
- Title: v0.4.0 → v0.5.0
- Architecture diagram: added auth flow (X-API-Key), per-user SSE, AlertRule/AlertEvent tables, login page
- Frontend table: added login-page, api-keys-page, alert-rules-page, alerts-list-page
- Hooks section: added fetch-with-auth, auth-api-client, auth-context, alert-api-client
- API endpoints table: rewrote with Auth column; added all /api/auth/*, /api/alert-rules/*, /api/alerts/* endpoints
- Database section: rewrote with User, ApiKey, AlertRule, AlertEvent models (with field details)
- SSE Bus: added per-user filtering, alert_fired event
- Added "Auth Modules" + "Alert Modules" subsections describing each file
- Testing: updated to 86 tests / 86% coverage; added test_auth_routes + test_alert_routes
- Data Flow: updated trace creation flow to include auth; added alert evaluation flow diagram
- Env vars: added AGENTLENS_JWT_SECRET
- Future Scaling: replaced "Multi-Tenant" (done) with "RBAC"

### codebase-summary.md
- Version: v0.2.0 → v0.5.0
- Stats: server tests 38→86, coverage >82%→86%
- Pages section: 3 files → 7 files (added login, api-keys, replay, alert-rules, alerts-list pages)
- Hooks section: 5 files → 9 files (added auth and alert clients)
- Server section: complete rewrite — auth_models/storage/routes, alert_models/storage/routes, alert_evaluator/notifier, otel_mapper all documented
- Test coverage table: added auth_routes, alert_routes, otel_mapper rows; total 90→139 tests
- Production build: updated to v0.5.0 with AGENTLENS_JWT_SECRET env
- Known limitations: removed done items, added JWT restart caveat + OTLP limitation

### project-overview-pdr.md
- Version: v0.4.0 → v0.5.0
- Core value prop: added alerting + multi-tenant auth bullets
- Distribution: Docker tag v0.4.0 → v0.5.0
- Functional requirements: added F8 (auth) + F9 (alerting); F7 renamed F10 with updated counts
- Security NFR: replaced "no auth" with JWT/bcrypt/SHA-256/cross-tenant-404 details
- Key features: v0.4.0 → v0.5.0; added items 11 (auth) and 12 (alerting)
- Roadmap: marked alerting + auth as done; added RBAC + TS framework integrations as next
- Success criteria: added Security criterion; F1-F7 → F1-F10; coverage >82% → 86%

## Unresolved Questions

None — all changes verified against actual server source files (alert_models.py, auth_models.py, alert_routes.py, auth_routes.py, auth_jwt.py, auth_deps.py, alert_evaluator.py, alert_notifier.py).
