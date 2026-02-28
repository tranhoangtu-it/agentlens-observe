# Phase 1: Alert Models & Storage

## Context Links
- [Current models](../../server/models.py) — SQLModel table definitions
- [Storage layer](../../server/storage.py) — CRUD functions, SQLite/PostgreSQL support
- [API endpoints](../../server/main.py) — FastAPI routes

## Overview
- **Priority:** P1 (foundation for all other phases)
- **Status:** pending
- **Description:** Define DB tables for alert rules and alert events. Add CRUD storage functions and REST API endpoints for managing rules and listing fired alerts.

## Key Insights
- Existing pattern: SQLModel tables in `models.py`, CRUD in `storage.py`, routes in `main.py`
- `init_db()` calls `SQLModel.metadata.create_all(engine)` — new tables auto-created on startup
- Tables must work with both SQLite and PostgreSQL (no DB-specific features)
- Keep models simple; v1 uses static thresholds only

## Requirements

### Functional
- AlertRule: user creates rules per agent with metric type, threshold, comparison operator, window size
- AlertEvent: system creates events when a rule fires, linking to triggering trace
- CRUD endpoints: create/list/update/delete rules; list events with filters
- Acknowledge/dismiss individual alerts

### Non-functional
- Tables indexed for common query patterns (agent_name, created_at, resolved)
- JSON serializable (no custom types that break SQLite)

## Architecture

### Data Model

```
AlertRule
  id: str (UUID, PK)
  agent_name: str (indexed) — which agent to monitor ("*" = all)
  metric: str — "cost", "error_rate", "latency", "missing_span"
  operator: str — "gt", "lt", "gte", "lte"
  threshold: float — comparison value
  window_size: int — number of recent traces to compare against (default 10)
  enabled: bool (default True)
  name: str — human-readable label
  webhook_url: str | None — optional webhook for this rule
  created_at: datetime
  updated_at: datetime

AlertEvent
  id: str (UUID, PK)
  rule_id: str (FK → AlertRule.id, indexed)
  trace_id: str (FK → Trace.id, indexed)
  agent_name: str (indexed)
  metric: str
  value: float — actual measured value
  threshold: float — rule threshold at time of firing
  message: str — human-readable description
  resolved: bool (default False)
  created_at: datetime (indexed)
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/alert-rules` | Create alert rule |
| GET | `/api/alert-rules` | List rules (filter by agent_name, metric) |
| PUT | `/api/alert-rules/{id}` | Update rule |
| DELETE | `/api/alert-rules/{id}` | Delete rule |
| GET | `/api/alerts` | List alert events (filter by agent, resolved, date) |
| PATCH | `/api/alerts/{id}/resolve` | Mark alert as resolved |
| GET | `/api/alerts/summary` | Unresolved count by severity (for header badge) |

## Related Code Files

### Files to modify
- `server/models.py` — add AlertRule, AlertEvent tables + request schemas
- `server/storage.py` — add alert CRUD functions
- `server/main.py` — add alert API routes

### Files to create
- `server/alert-models.py` — AlertRule, AlertEvent SQLModel tables (keep models.py under 200 lines)
- `server/alert-storage.py` — CRUD for alert rules and events
- `server/alert-routes.py` — FastAPI router for /api/alert-rules and /api/alerts

### Rationale for new files
- `models.py` is 81 lines; adding ~60 lines of alert models pushes near 200-line limit
- Separate files follow modularization rule and keep concerns isolated
- Use `APIRouter` in `alert-routes.py`, include in `main.py` with `app.include_router()`

## Implementation Steps

1. Create `server/alert-models.py`:
   - `AlertRule(SQLModel, table=True)` with fields above
   - `AlertEvent(SQLModel, table=True)` with fields above
   - Pydantic request schemas: `AlertRuleIn`, `AlertRuleUpdate`, `AlertEventFilter`
   - Add composite indexes: `(agent_name, metric)` on AlertRule, `(rule_id, created_at)` on AlertEvent

2. Create `server/alert-storage.py`:
   - `create_alert_rule(data) -> AlertRule`
   - `list_alert_rules(agent_name?, metric?, enabled?) -> list[AlertRule]`
   - `update_alert_rule(id, data) -> AlertRule | None`
   - `delete_alert_rule(id) -> bool`
   - `create_alert_event(data) -> AlertEvent`
   - `list_alert_events(agent_name?, resolved?, limit?, offset?) -> (list, total)`
   - `resolve_alert_event(id) -> AlertEvent | None`
   - `get_unresolved_alert_count() -> int`
   - Reuse `storage._get_engine()` for DB engine access

3. Create `server/alert-routes.py`:
   - `router = APIRouter(prefix="/api", tags=["alerts"])`
   - Wire all 7 endpoints from table above
   - Import router in `main.py`: `from alert_routes import router as alert_router; app.include_router(alert_router)`

4. Update `server/main.py`:
   - Add `from alert_routes import router as alert_router` (use underscore import name for Python module)
   - Add `app.include_router(alert_router)` before static mount

5. Note: Python import requires underscore file name. Use `alert_models.py`, `alert_storage.py`, `alert_routes.py` (underscore, not kebab) for Python files. Kebab-case is for TS/JS files only.

## Todo List
- [ ] Create `server/alert_models.py` with AlertRule + AlertEvent tables
- [ ] Create `server/alert_storage.py` with CRUD functions
- [ ] Create `server/alert_routes.py` with APIRouter endpoints
- [ ] Update `server/main.py` to include alert router
- [ ] Verify tables auto-create on `init_db()`
- [ ] Test all endpoints manually with httpx/curl

## Success Criteria
- `init_db()` creates alert_rule and alert_event tables
- All 7 API endpoints return correct responses
- Works with both SQLite and PostgreSQL
- Each new file under 200 lines

## Risk Assessment
- **Foreign key constraints**: SQLite doesn't enforce FK by default. Use `PRAGMA foreign_keys=ON` or skip FK constraints and rely on application logic (simpler, matches existing pattern where Span.trace_id has no FK constraint)
- **Migration**: No migration tool in use — `create_all` handles new tables but not schema changes to existing ones

## Security Considerations
- Validate webhook_url format (must be valid HTTP/HTTPS URL)
- Rate-limit alert creation to prevent DB bloat from rapid-fire rules
- No auth in v1 (single-tenant) — deferred to multi-tenant auth phase
