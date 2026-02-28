# Phase 3: Alert Dashboard UI

## Context Links
- [Phase 1 — Models](./phase-01-alert-models-and-storage.md)
- [App routing](../../dashboard/src/App.tsx) — hash-based router, sidebar nav
- [API client](../../dashboard/src/lib/api-client.ts) — typed fetch wrappers
- [SSE hook](../../dashboard/src/lib/use-sse-traces.ts) — EventSource pattern
- [Traces list page](../../dashboard/src/pages/traces-list-page.tsx) — reference for page structure

## Overview
- **Priority:** P2 (depends on phases 1-2)
- **Status:** pending
- **Description:** Add alerts page to dashboard — list fired alerts, manage alert rules, show unresolved alert count badge in sidebar. Receive real-time alert_fired SSE events.

## Key Insights
- Existing routing: hash-based in App.tsx, no React Router — add new route pattern `#/alerts`
- Sidebar has single nav item ("Traces") — add "Alerts" with bell icon + unresolved count badge
- Follow existing patterns: page component in `pages/`, data fetching in component, SSE for live updates
- Radix UI primitives available for dialogs/forms (already in package.json)
- Keep each component file under 200 lines

## Requirements

### Functional
- **Alerts list page** (`#/alerts`): table of fired alerts with status, agent, metric, value, timestamp, link to trace
- **Alert rules panel** (`#/alerts/rules`): list rules, create/edit/delete with form dialog
- **Header badge**: unresolved alert count in sidebar "Alerts" nav item
- **Real-time**: new alerts appear instantly via SSE `alert_fired` event
- **Resolve action**: button to mark alert as resolved

### Non-functional
- Consistent with existing design (dark theme, Tailwind classes, Radix UI)
- Lazy-load alerts page (rarely visited vs traces list)
- Responsive table with pagination

## Architecture

### Routes

| Hash | Component | Description |
|------|-----------|-------------|
| `#/alerts` | AlertsListPage | List fired alert events |
| `#/alerts/rules` | AlertRulesPage | Manage alert rules |

### Component Tree

```
App.tsx
├── Sidebar
│   └── NavItem "Alerts" (bell icon + badge count)
├── #/alerts → AlertsListPage
│   ├── AlertsTable (sortable, filterable)
│   └── PaginationControls (reuse existing)
└── #/alerts/rules → AlertRulesPage
    ├── AlertRulesList (table of rules)
    └── AlertRuleDialog (create/edit form)
```

### New Files

```
dashboard/src/
├── pages/
│   ├── alerts-list-page.tsx       — fired alerts table page
│   └── alert-rules-page.tsx       — rule management page
├── components/
│   ├── alerts-table.tsx           — alert events table
│   ├── alert-rules-list.tsx       — rules table with actions
│   └── alert-rule-dialog.tsx      — create/edit rule form dialog
└── lib/
    ├── alert-api-client.ts        — fetch wrappers for alert endpoints
    └── use-sse-alerts.ts          — SSE hook for alert_fired events
```

## Related Code Files

### Files to create
- `dashboard/src/pages/alerts-list-page.tsx`
- `dashboard/src/pages/alert-rules-page.tsx`
- `dashboard/src/components/alerts-table.tsx`
- `dashboard/src/components/alert-rules-list.tsx`
- `dashboard/src/components/alert-rule-dialog.tsx`
- `dashboard/src/lib/alert-api-client.ts`
- `dashboard/src/lib/use-sse-alerts.ts`

### Files to modify
- `dashboard/src/App.tsx` — add routes, sidebar nav item with badge
- `dashboard/src/lib/use-sse-traces.ts` — optionally extend to handle alert_fired events (or use separate hook)

## Implementation Steps

1. **Create `alert-api-client.ts`**:
   - TypeScript interfaces: `AlertRule`, `AlertEvent`, `AlertRuleIn`, `AlertsSummary`
   - Functions: `fetchAlertRules()`, `createAlertRule()`, `updateAlertRule()`, `deleteAlertRule()`, `fetchAlerts()`, `resolveAlert()`, `fetchAlertsSummary()`
   - Follow existing `api-client.ts` pattern (BASE + fetch + error handling)

2. **Create `use-sse-alerts.ts`**:
   - Listen for `alert_fired` SSE event type on existing `/api/traces/stream` endpoint
   - Return `{ latestAlert, unresolvedCount }` — count fetched from `/api/alerts/summary`
   - Re-fetch summary on each `alert_fired` event

3. **Create `alerts-table.tsx`**:
   - Columns: Status (resolved/active), Agent, Metric, Value, Threshold, Message, Trace (link), Time, Actions (resolve button)
   - Reuse existing table styling from `trace-list-table.tsx`
   - Color-code: red for active, muted for resolved

4. **Create `alerts-list-page.tsx`**:
   - Fetch alerts with pagination, filter by agent/resolved status
   - Integrate SSE hook for live updates
   - "Manage Rules" button links to `#/alerts/rules`

5. **Create `alert-rules-list.tsx`**:
   - Table: Name, Agent, Metric, Mode, Threshold, Enabled toggle, Actions (edit/delete)
   - "Create Rule" button opens dialog

6. **Create `alert-rule-dialog.tsx`**:
   - Form fields: name, agent_name (dropdown from `/api/agents` + "*" option), metric (select), mode (absolute/relative), operator (select), threshold (number), window_size (number), webhook_url (optional), enabled (toggle)
   - Used for both create and edit (pass existing rule data as prop)

7. **Create `alert-rules-page.tsx`**:
   - Compose AlertRulesList + AlertRuleDialog
   - Fetch rules on mount, refetch after create/update/delete

8. **Update `App.tsx`**:
   - Add Route types: `{ name: 'alerts' }`, `{ name: 'alert-rules' }`
   - Add parseHash patterns: `alerts/rules` and `alerts`
   - Add sidebar NavItem with `Bell` icon from lucide-react
   - Add badge component showing unresolved count (from SSE hook or polling)
   - Lazy-load both alert pages
   - Add breadcrumb entries for alert routes

## Todo List
- [ ] Create `alert-api-client.ts` with all fetch wrappers
- [ ] Create `use-sse-alerts.ts` hook
- [ ] Create `alerts-table.tsx` component
- [ ] Create `alerts-list-page.tsx` page
- [ ] Create `alert-rules-list.tsx` component
- [ ] Create `alert-rule-dialog.tsx` form dialog
- [ ] Create `alert-rules-page.tsx` page
- [ ] Update `App.tsx` with routes + sidebar nav + badge
- [ ] Verify all files under 200 lines
- [ ] Test UI manually with sample data

## Success Criteria
- Alerts page shows fired alerts with correct data
- Rules page allows full CRUD on alert rules
- Sidebar badge shows unresolved count, updates in real-time via SSE
- New alerts appear in list without page refresh
- Navigation between traces and alerts works correctly
- All component files under 200 lines

## Risk Assessment
- **Radix UI Dialog**: verify it's already installed in package.json. If not, add `@radix-ui/react-dialog`
- **Form validation**: keep client-side simple (required fields only); server validates

## Security Considerations
- Webhook URL field: display warning that URL will be called from server
- No sensitive data in alert messages (only metric values and thresholds)
