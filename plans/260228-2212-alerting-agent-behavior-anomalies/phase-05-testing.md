# Phase 5: Testing

## Context Links
- [Test conftest](../../server/tests/conftest.py) — fixtures pattern
- [API endpoint tests](../../server/tests/test_api_endpoints.py) — reference test structure
- [OTel tests](../../server/tests/test_otel_ingestion.py) — integration test pattern

## Overview
- **Priority:** P2 (final phase)
- **Status:** pending
- **Description:** Comprehensive tests for alert models, storage, evaluator, API endpoints, and notifications. Target: 15+ new tests covering all phases.

## Key Insights
- Existing test pattern: `conftest.py` provides `test_db`, `client`, `sample_trace_data` fixtures
- Tests use `TestClient` from FastAPI for endpoint tests
- Each test gets fresh DB (SQLite temp file per test)
- Test classes grouped by feature area

## Requirements

### Functional
- Unit tests for alert evaluator metric computations
- Unit tests for threshold comparison (absolute + relative modes)
- Integration tests for alert API endpoints (CRUD rules, list events)
- Integration tests for end-to-end alert firing (ingest trace -> alert event created)
- Test webhook delivery (mock httpx)

### Non-functional
- All tests pass with both SQLite and PostgreSQL
- No test depends on another test's state
- Tests complete in <10s total

## Related Code Files

### Files to create
- `server/tests/test_alert_models.py` — model validation tests
- `server/tests/test_alert_evaluator.py` — evaluator unit tests
- `server/tests/test_alert_api_endpoints.py` — API endpoint integration tests

### Files to modify
- `server/tests/conftest.py` — add alert-specific fixtures (sample rule data, sample trace with anomaly)

## Implementation Steps

1. **Update `conftest.py`** — add fixtures:
   ```python
   @pytest.fixture
   def sample_alert_rule_data():
       return {
           "name": "Cost spike alert",
           "agent_name": "search_agent",
           "metric": "cost",
           "mode": "absolute",
           "operator": "gt",
           "threshold": 0.10,
           "window_size": 10,
           "enabled": True,
       }

   @pytest.fixture
   def sample_expensive_trace_data():
       """Trace with high cost to trigger alerts."""
       # ... trace with total_cost_usd > 0.10
   ```

2. **Create `test_alert_models.py`** (~40 lines):
   - `test_alert_rule_creation` — create rule, verify fields
   - `test_alert_event_creation` — create event, verify fields
   - `test_alert_rule_defaults` — verify default values (enabled=True, mode=absolute)

3. **Create `test_alert_evaluator.py`** (~120 lines):
   - `TestMetricComputation`:
     - `test_compute_cost` — verify cost extraction from trace
     - `test_compute_error_rate` — verify error span counting
     - `test_compute_latency` — verify duration extraction
     - `test_check_missing_spans` — verify span name matching
   - `TestThresholdEvaluation`:
     - `test_absolute_gt_triggers` — value > threshold fires
     - `test_absolute_gt_no_trigger` — value < threshold doesn't fire
     - `test_relative_mode_triggers` — value > multiplier * baseline fires
     - `test_relative_mode_no_baseline` — first trace skips relative rules
   - `TestEvaluateAlertRules`:
     - `test_end_to_end_cost_alert` — ingest expensive trace, verify AlertEvent created
     - `test_disabled_rule_skipped` — disabled rule doesn't fire
     - `test_wildcard_agent_matches` — rule with agent_name="*" fires for any agent
     - `test_evaluation_error_doesnt_block` — evaluator exception doesn't raise

4. **Create `test_alert_api_endpoints.py`** (~150 lines):
   - `TestAlertRulesCRUD`:
     - `test_create_rule` — POST /api/alert-rules returns 201
     - `test_list_rules` — GET /api/alert-rules returns rules
     - `test_update_rule` — PUT /api/alert-rules/{id} updates
     - `test_delete_rule` — DELETE /api/alert-rules/{id} removes
     - `test_create_rule_invalid_metric` — 422 for bad metric
   - `TestAlertEvents`:
     - `test_list_alerts_empty` — GET /api/alerts returns empty list
     - `test_resolve_alert` — PATCH /api/alerts/{id}/resolve marks resolved
     - `test_alerts_summary` — GET /api/alerts/summary returns count
   - `TestEndToEndAlertFiring`:
     - `test_ingest_trace_fires_cost_alert` — create rule, ingest expensive trace, verify alert event in DB
     - `test_ingest_trace_no_alert_below_threshold` — ingest cheap trace, verify no alert

## Todo List
- [ ] Add alert fixtures to `conftest.py`
- [ ] Create `test_alert_models.py`
- [ ] Create `test_alert_evaluator.py` with unit tests
- [ ] Create `test_alert_api_endpoints.py` with integration tests
- [ ] Run full test suite — verify no regressions
- [ ] Verify all new tests pass with SQLite
- [ ] Check coverage delta

## Success Criteria
- 15+ new tests added
- All tests pass (including existing 46+)
- No regressions in existing test suite
- End-to-end flow tested: rule creation -> trace ingestion -> alert event firing
- Each test file under 200 lines

## Risk Assessment
- **Webhook tests**: mock `httpx.post` to avoid external calls. Use `unittest.mock.patch`
- **SSE tests**: SSE event publishing is synchronous — verify `bus.publish` called with correct args using mock
- **Test isolation**: each test gets fresh DB; alert rules from one test don't leak to another

## Security Considerations
- Test data should not include real API keys or URLs
- Webhook test should mock external calls, never make real HTTP requests
