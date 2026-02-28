# Phase 2: Alert Evaluation Engine

## Context Links
- [Phase 1 — Models & Storage](./phase-01-alert-models-and-storage.md)
- [Trace ingestion](../../server/main.py#L50-L58) — `ingest_trace()` endpoint
- [Span ingestion](../../server/main.py#L64-L91) — `ingest_spans()` endpoint
- [Storage aggregates](../../server/storage.py#L64-L73) — cost/duration computation

## Overview
- **Priority:** P1 (core logic)
- **Status:** pending
- **Description:** Evaluate alert rules against incoming traces. Fires on trace completion (all spans have `end_ms`). Computes rolling baselines from recent traces and compares against rule thresholds.

## Key Insights
- Evaluation triggers when `status` transitions to `"completed"` — both in `create_trace()` and `add_spans_to_trace()`
- Rolling baseline = query last N completed traces for same agent, compute avg of target metric
- For "missing_span" check: compare span names in current trace against expected pattern defined in rule threshold (stored as JSON)
- Keep evaluation synchronous in v1 (trace ingestion is already fast); async deferred to v2

## Requirements

### Functional
- **Cost spike**: alert if `trace.total_cost_usd > threshold` OR if cost > `multiplier * avg(last N traces)`
- **Error rate**: alert if `error_spans / total_spans > threshold` (where error = span without end_ms or with error metadata)
- **Latency anomaly**: alert if `trace.duration_ms > threshold` OR if duration > `multiplier * avg(last N traces)`
- **Missing span**: alert if expected span name (from rule config) not found in trace's span list

### Non-functional
- Evaluation must not block trace ingestion (fail silently, log errors)
- Must handle edge cases: first trace for agent (no baseline), agent with "*" wildcard

## Architecture

### Evaluation Flow

```
Trace Ingestion (create_trace / add_spans_to_trace)
  └── if trace.status == "completed":
        └── evaluate_alert_rules(trace_id, agent_name)
              ├── fetch enabled rules for agent (+ wildcard "*")
              ├── for each rule:
              │   ├── compute metric value from trace
              │   ├── if metric uses baseline: query last N traces
              │   ├── compare value against threshold
              │   └── if triggered: create AlertEvent + publish SSE + call webhook
              └── catch all exceptions (never block ingestion)
```

### Metric Computation

| Metric | Value Source | Baseline |
|--------|------------|----------|
| `cost` | `trace.total_cost_usd` | avg cost of last N traces |
| `error_rate` | `count(spans without end_ms) / span_count` | N/A (absolute threshold) |
| `latency` | `trace.duration_ms` | avg duration of last N traces |
| `missing_span` | set(span.name for span in trace) | expected span names from rule config |

### Rule Threshold Semantics

For `cost` and `latency`:
- `operator="gt", threshold=0.10` means "alert if cost > $0.10" (absolute)
- `operator="gt", threshold=5.0, window_size=10` with metric `cost` means "alert if cost > 5x the average of last 10 traces" (relative multiplier)

Decision: use a `mode` field on AlertRule — `"absolute"` or `"relative"`. Default `"absolute"`.
- Absolute: compare value directly against threshold
- Relative: threshold is a multiplier; compare `value > threshold * baseline_avg`

For `missing_span`:
- `threshold` field stores JSON string of expected span names: `'["web_search", "summarize"]'`
- Alert fires if any expected span name is missing from trace

## Related Code Files

### Files to create
- `server/alert_evaluator.py` — pure function `evaluate_alert_rules(trace_id, agent_name)` + metric computation helpers

### Files to modify
- `server/main.py` — call `evaluate_alert_rules()` after trace completion in `ingest_trace()` and `ingest_spans()`
- `server/alert_models.py` — add `mode` field to AlertRule (`"absolute"` | `"relative"`)

## Implementation Steps

1. Add `mode: str = Field(default="absolute")` to `AlertRule` in `alert_models.py`

2. Create `server/alert_evaluator.py`:
   - `def evaluate_alert_rules(trace_id: str, agent_name: str) -> list[AlertEvent]:`
     - Query enabled rules where `agent_name` matches or rule.agent_name == "*"
     - For each rule, call appropriate metric function
     - Return list of created AlertEvent objects (for SSE/webhook in phase 4)
   - `def _compute_cost(trace) -> float | None`
   - `def _compute_error_rate(spans) -> float`
   - `def _compute_latency(trace) -> float | None`
   - `def _check_missing_spans(spans, expected_names: list[str]) -> list[str]`
   - `def _get_baseline_avg(agent_name: str, metric: str, window: int) -> float | None`
     - Query last N completed traces, return avg of metric field
   - `def _evaluate_threshold(value, baseline_avg, rule) -> bool`
     - Absolute mode: `value <operator> threshold`
     - Relative mode: `value <operator> (threshold * baseline_avg)`
   - Wrap entire function in try/except — log errors, never raise

3. Update `server/main.py` — `ingest_trace()`:
   - After `create_trace()`, if `trace.status == "completed"`: call `evaluate_alert_rules(trace.id, trace.agent_name)`
   - Same in `ingest_spans()`: after `add_spans_to_trace()`, check if returned trace.status == "completed"
   - Same in `ingest_otel_traces()`: after trace creation/update

4. Handle edge cases:
   - First trace for agent: skip relative mode rules (no baseline), still evaluate absolute rules
   - Agent with no completed traces in window: skip relative evaluation
   - Missing cost/duration on trace: skip that metric

## Todo List
- [ ] Add `mode` field to AlertRule model
- [ ] Create `server/alert_evaluator.py` with evaluation logic
- [ ] Add metric computation functions (cost, error_rate, latency, missing_span)
- [ ] Add baseline computation (`_get_baseline_avg`)
- [ ] Wire evaluation into `ingest_trace()` endpoint
- [ ] Wire evaluation into `ingest_spans()` endpoint
- [ ] Wire evaluation into `ingest_otel_traces()` endpoint
- [ ] Handle edge cases (first trace, missing data)
- [ ] Verify evaluation doesn't block ingestion on error

## Success Criteria
- Alert rules fire correctly for all 4 metric types
- Relative mode computes correct baseline from last N traces
- Evaluation errors logged but never block trace ingestion
- Works with both SQLite and PostgreSQL

## Risk Assessment
- **Performance**: querying last N traces on every ingestion could be slow with large DBs. Mitigation: add index on `(agent_name, status, created_at)` — already exists as `ix_trace_agent_created`
- **Race condition**: concurrent trace ingestion could compute stale baselines. Acceptable for v1 (thresholds are approximate)
- **Alert storms**: rapid trace ingestion could fire many alerts. Mitigation: add simple cooldown — skip rule if last AlertEvent for same rule was < 60s ago

## Security Considerations
- `missing_span` threshold is parsed as JSON — validate it's a list of strings, not arbitrary JSON
- Webhook URLs called from server — validate HTTPS only in production
