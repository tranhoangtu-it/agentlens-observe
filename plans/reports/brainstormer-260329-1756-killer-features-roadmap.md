# AgentLens Killer Features — Prioritization & Roadmap

**Date:** 2026-03-29
**Type:** Brainstorm Report
**Target:** Solo devs / startups
**LLM Strategy:** BYO API key (user provides own key)

---

## Impact/Effort Matrix

| # | Feature | Impact | Effort | Moat | Priority |
|---|---------|--------|--------|------|----------|
| 1 | AI Failure Autopsy | Very High | Medium | ⭐⭐⭐⭐⭐ | **P0** |
| 5 | MCP Protocol Tracing | Very High | Medium | ⭐⭐⭐⭐⭐ | **P0** |
| 9 | Plugin System | High | High | ⭐⭐⭐⭐ | **P1** |
| 6 | Prompt Versioning | High | Medium | ⭐⭐⭐⭐ | **P1** |
| 7 | LLM-as-Judge Eval | High | Medium | ⭐⭐⭐⭐ | **P1** |
| 2 | Agent Replay Sandbox | Very High | Very High | ⭐⭐⭐⭐⭐ | **P2** |
| 3 | CLI Tool (Go) | Medium | Medium | ⭐⭐⭐ | **P2** |
| 8 | VS Code Extension | High | Medium | ⭐⭐⭐ | **P2** |
| 4 | .NET SDK | Medium | Low | ⭐⭐⭐⭐ | **P3** |
| 10 | Dashboard updates | Medium | Low-Med | ⭐⭐ | **Ongoing** |

---

## Feature Designs

### 1. AI-Powered Failure Autopsy (P0)

**Files:**
```
server/autopsy_routes.py        — POST /api/traces/{id}/autopsy
server/autopsy_analyzer.py      — Build prompt from trace, call LLM
server/autopsy_models.py        — AutopsyRequest, AutopsyResult
server/autopsy_storage.py       — Cache results in DB
server/llm_provider.py          — BYO API key dispatcher (shared with Eval)
dashboard/src/components/autopsy-panel.tsx
dashboard/src/lib/autopsy-api-client.ts
dashboard/src/pages/settings-page.tsx  — API key config
```

**Flow:**
1. User clicks "Autopsy" on failed/slow trace
2. Server builds structured prompt: span tree + errors + timing + costs
3. Calls LLM via user's API key (stored encrypted in DB)
4. Returns: root cause, affected spans, suggested fix, severity
5. Cache result — avoid re-analyzing same trace

**BYO API key shared infra:** Settings page stores encrypted API key + provider choice. `llm_provider.py` abstracts OpenAI/Anthropic/Gemini calls. Used by both Autopsy and Eval.

---

### 2. Agent Replay Sandbox (P2)

**Recommended scope: Mock Replay (deterministic, free)**

**Files:**
```
server/replay_routes.py         — POST /api/traces/{id}/replay
server/replay_engine.py         — Build mock execution plan
server/replay_models.py         — ReplayConfig, ReplayResult
sdk/agentlens/replay.py         — Client-side replay runtime
dashboard/src/pages/trace-replay-sandbox-page.tsx
dashboard/src/components/replay-diff-viewer.tsx
```

**Flow:**
1. User selects trace → "Replay Sandbox"
2. Dashboard shows span tree, user edits input at any span
3. SDK replay runtime runs agent with mock responses (captured outputs for unchanged spans, real LLM for modified spans)
4. Side-by-side diff: original vs replayed

**Depends on:** Plugin System (P1) for SDK hooks

---

### 3. CLI Tool — Go (P2)

**Recommended scope: Dev workflow (query + tail + pipe)**

**Files:**
```
cli/
  cmd/root.go, traces.go, push.go, config.go, version.go
  internal/api/client.go
  internal/output/formatter.go
  internal/stream/sse.go
  go.mod
```

**Commands:**
```bash
agentlens traces list --status=error --limit=10
agentlens traces show <id>
agentlens traces tail              # SSE real-time
agentlens traces diff <id1> <id2>
cat trace.json | agentlens push    # pipe ingestion
agentlens config set endpoint/api-key
```

---

### 4. .NET SDK (P3)

**Files:**
```
sdk-dotnet/src/AgentLens/
  AgentLensClient.cs, Tracer.cs, Transport.cs, SpanData.cs, Cost.cs
  Integrations/SemanticKernelIntegration.cs, AutoGenIntegration.cs
sdk-dotnet/tests/AgentLens.Tests/
```

**Pattern:** Mirror Python SDK. AsyncLocal<T> for context, HttpClient for transport.

**Timing:** Ship when .NET agent ecosystem (Semantic Kernel, AutoGen.NET) matures.

---

### 5. MCP Protocol Tracing (P0)

**Files:**
```
sdk/agentlens/integrations/mcp.py       — MCP Python middleware
sdk-ts/src/integrations/mcp.ts           — MCP TypeScript integration
server/mcp_models.py                     — MCP span types & metadata
dashboard/src/components/mcp-tool-call-panel.tsx
dashboard/src/components/mcp-flow-graph.tsx
```

**Span types:** `mcp.tool_call`, `mcp.resource_read`, `mcp.prompt_get`
**Metadata:** server_name, tool_name, arguments, response, latency
**Integration:** Wrap MCP client transport layer (JSON-RPC)

---

### 6. Prompt Versioning (P1)

**Files:**
```
server/prompt_models.py         — PromptTemplate, PromptVersion tables
server/prompt_storage.py        — CRUD + version diff
server/prompt_routes.py         — /api/prompts endpoints
dashboard/src/pages/prompt-registry-page.tsx
dashboard/src/components/prompt-diff-viewer.tsx, prompt-usage-chart.tsx
```

**Data model:** PromptTemplate (id, name, latest_version) → PromptVersion (id, prompt_id, version, content, variables, created_at)
**SDK:** `lens.prompt("name", v=3, vars={...})` → auto-log in span metadata

---

### 7. LLM-as-Judge Eval (P1)

**Files:**
```
server/eval_models.py           — EvalCriteria, EvalRun, EvalResult
server/eval_routes.py           — /api/evals endpoints
server/eval_runner.py           — Orchestrate judge LLM calls
server/eval_prompts.py          — Judge prompt templates
dashboard/src/pages/eval-dashboard-page.tsx
dashboard/src/components/eval-score-card.tsx, eval-criteria-editor.tsx
```

**Flow:** Define criteria + rubric → select traces → LLM judges → scores + trends
**Link to Prompt Versioning:** Compare eval scores across prompt versions

---

### 8. VS Code Extension (P2)

**Files:**
```
vscode-extension/src/
  extension.ts, trace-tree-provider.ts, trace-detail-webview.ts
  span-codelens.ts, status-bar.ts
  package.json
```

**Features:** Sidebar trace list, WebView detail, CodeLens on @trace decorators, status bar

---

### 9. Plugin System (P1)

**SDK-side:**
```python
# sdk/agentlens/plugins.py
class SpanProcessor(Protocol):
    def on_start(self, span: SpanData) -> None: ...
    def on_end(self, span: SpanData) -> None: ...

configure(processors=[...], exporters=[...])
```

**Server-side:**
```python
# server/plugin_loader.py
class ServerPlugin(Protocol):
    name: str
    def on_trace_created(self, trace: Trace) -> None: ...
    def on_trace_completed(self, trace: Trace) -> None: ...
    def register_routes(self, app: FastAPI) -> None: ...

# Auto-discover from server/plugins/ directory
```

---

## Roadmap

```
Phase 1 — "Differentiate" (~4 weeks)
├── MCP Protocol Tracing (SDK + Server + Dashboard)
├── AI-Powered Failure Autopsy (Server + Dashboard)
└── BYO API Key Settings (shared infra for AI features)

Phase 2 — "Platform" (~6 weeks)
├── Plugin System (SDK + Server foundation)
├── Prompt Versioning (Server + Dashboard)
└── LLM-as-Judge Eval (Server + Dashboard)

Phase 3 — "DX & Power" (~8 weeks)
├── Agent Replay Sandbox (depends on Plugin System)
├── CLI Tool in Go (independent)
└── VS Code Extension (independent, parallelizable with CLI)

Phase 4 — "Expand" (~3 weeks)
└── .NET SDK (ship when .NET agent ecosystem matures)
```

---

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| MCP + Autopsy as P0 | No competitor has either. First mover advantage. |
| Mock replay over full re-execute | Deterministic, free, good enough for debugging |
| CLI scope = dev workflow | Solo devs need `tail` + `push`, not admin CLI |
| Plugin System before Replay | Replay needs SDK hooks that plugins provide |
| .NET deferred to P3 | Market too small today, monitor growth |
| BYO API key, not hosted | Zero infra cost, user controls data, simpler security |

---

## Unresolved Questions
1. MCP transport wrapping: monkey-patch vs official middleware API? Need to check MCP SDK extension points.
2. Autopsy prompt: structured output (JSON mode) vs free-form? JSON more parseable but less nuanced.
3. Eval scoring: numeric (1-5) vs categorical (pass/fail) vs both?
4. Plugin System: hot-reload plugins without server restart?
5. .NET SDK: target .NET 8 LTS only or also .NET 9?
