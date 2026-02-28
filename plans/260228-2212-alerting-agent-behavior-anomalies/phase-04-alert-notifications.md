# Phase 4: Alert Notifications (SSE + Webhook)

## Context Links
- [Phase 2 — Evaluator](./phase-02-alert-evaluation-engine.md) — triggers notifications
- [SSE bus](../../server/sse.py) — existing publish/subscribe pattern
- [SSE in main.py](../../server/main.py#L221-L227) — stream endpoint

## Overview
- **Priority:** P2 (depends on phases 1-2)
- **Status:** pending
- **Description:** When alert evaluator fires an alert, push notification via SSE event and optionally call configured webhook URL.

## Key Insights
- SSE bus already supports named events (`bus.publish("event_type", data)`)
- Dashboard SSE hook can listen for new event type with `es.addEventListener("alert_fired", handler)`
- Webhook delivery must be async/non-blocking — use `httpx.AsyncClient` or fire-and-forget thread
- Keep webhook simple: POST JSON payload to URL, no retry logic in v1

## Requirements

### Functional
- Publish `alert_fired` SSE event when AlertEvent created
- Call webhook URL (if configured on rule) with alert payload
- Webhook payload: `{ rule_name, agent_name, metric, value, threshold, trace_id, message, timestamp }`

### Non-functional
- Webhook calls must not block trace ingestion (timeout: 5s, fire-and-forget)
- SSE publish is already non-blocking (existing pattern)

## Architecture

### Notification Flow

```
alert_evaluator.evaluate_alert_rules()
  └── for each triggered rule:
        ├── create_alert_event() in DB
        ├── bus.publish("alert_fired", event_data)  ← SSE push
        └── if rule.webhook_url:
              └── _send_webhook(rule.webhook_url, payload)  ← async, non-blocking
```

### Webhook Payload Schema

```json
{
  "event": "alert_fired",
  "rule_name": "Cost spike - SearchAgent",
  "agent_name": "search_agent",
  "metric": "cost",
  "mode": "relative",
  "value": 0.52,
  "threshold": 5.0,
  "baseline_avg": 0.08,
  "trace_id": "trace-abc-123",
  "message": "Cost $0.52 is 6.5x the average ($0.08) for search_agent",
  "timestamp": "2026-02-28T22:12:00Z"
}
```

## Related Code Files

### Files to create
- `server/alert_notifier.py` — `notify_alert(event, rule)` function handling SSE + webhook

### Files to modify
- `server/alert_evaluator.py` — call `notify_alert()` after creating AlertEvent
- `server/sse.py` — no changes needed (already supports arbitrary event types)

## Implementation Steps

1. Create `server/alert_notifier.py`:
   - `def notify_alert(alert_event: AlertEvent, rule: AlertRule, baseline_avg: float | None) -> None:`
     - Build payload dict from alert_event + rule fields
     - `bus.publish("alert_fired", payload)` for SSE
     - If `rule.webhook_url`: spawn `_send_webhook()` in background thread
   - `def _send_webhook(url: str, payload: dict) -> None:`
     - `import httpx` (already in server requirements)
     - `httpx.post(url, json=payload, timeout=5.0)` in try/except
     - Log success/failure, never raise

2. Update `server/alert_evaluator.py`:
   - Import `notify_alert` from `alert_notifier`
   - After `create_alert_event()`, call `notify_alert(event, rule, baseline_avg)`
   - Pass `baseline_avg` so webhook payload includes context

3. Verify SSE integration:
   - Dashboard `use-sse-alerts.ts` hook listens for `alert_fired` event
   - Payload matches TypeScript interface defined in phase 3

## Todo List
- [ ] Create `server/alert_notifier.py` with SSE + webhook delivery
- [ ] Wire notifier into alert evaluator
- [ ] Test SSE event delivery to dashboard
- [ ] Test webhook delivery with httpbin or similar
- [ ] Verify non-blocking behavior (webhook timeout doesn't stall ingestion)

## Success Criteria
- SSE clients receive `alert_fired` events in real-time
- Webhook POST delivers correct JSON payload
- Webhook failure doesn't affect trace ingestion or SSE delivery
- Dashboard badge updates immediately when alert fires

## Risk Assessment
- **Webhook abuse**: users could configure webhook to internal network. Mitigation for v1: document that webhook calls originate from server. SSRF protection deferred to v2.
- **Thread safety**: `bus.publish()` is called from main thread. Webhook runs in separate thread. No shared mutable state — safe.

## Security Considerations
- Validate webhook_url: must start with `http://` or `https://`
- Consider HTTPS-only in production mode (env var toggle)
- Don't include trace input/output in webhook payload (could contain sensitive data)
