---
title: "Alerting on Agent Behavior Anomalies"
description: "Detect cost spikes, error rate increases, latency anomalies, and missing spans with configurable alert rules"
status: pending
priority: P2
effort: 12h
branch: kai/feat/alerting-agent-behavior-anomalies
tags: [alerting, anomaly-detection, observability, sse]
created: 2026-02-28
---

# Alerting on Agent Behavior Anomalies

## Summary

Add an alerting system that detects anomalies in agent behavior: cost spikes, error rate increases, latency anomalies, and missing expected spans. Users configure alert rules per agent, and alerts fire in real-time during trace ingestion. Alerts display in a dashboard page and push via SSE + optional webhooks.

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Alert storage | New DB tables (`alert_rule`, `alert_event`) | Persistent, queryable, survives restarts |
| Evaluation | Real-time on trace ingestion | Simpler than cron; immediate feedback |
| Delivery | SSE push + webhook (optional) | SSE already exists; webhooks cover Slack/PagerDuty |
| Rule config | User-configurable thresholds | Static thresholds v1; z-score deferred to v2 |
| Baseline | Rolling window (last N traces) | Simple to compute, no external deps |

## Phases

| # | Phase | Status | Effort | File |
|---|-------|--------|--------|------|
| 1 | Alert models & storage | pending | 2h | [phase-01](./phase-01-alert-models-and-storage.md) |
| 2 | Alert evaluation engine | pending | 3h | [phase-02](./phase-02-alert-evaluation-engine.md) |
| 3 | Alert dashboard UI | pending | 4h | [phase-03](./phase-03-alert-dashboard-ui.md) |
| 4 | Alert notifications (SSE + webhook) | pending | 2h | [phase-04](./phase-04-alert-notifications.md) |
| 5 | Testing | pending | 1h | [phase-05](./phase-05-testing.md) |

## Key Dependencies

- Existing SSE bus (`server/sse.py`) for real-time push
- SQLModel tables (`server/models.py`) for DB schema
- React hash router (`dashboard/src/App.tsx`) for new alerts page
- API client (`dashboard/src/lib/api-client.ts`) for fetch wrappers

## Scope Boundaries (v1)

**In scope:** static threshold rules, 4 anomaly types, dashboard page, SSE alerts, webhook delivery
**Out of scope:** statistical z-score detection, email delivery, alert grouping/deduplication, ML-based anomaly detection
