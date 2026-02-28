# AgentLens

**Debug AI agents visually** — self-hosted, open-source, agent-native observability.

> Unlike LangSmith (paid, cloud-only) and Langfuse (LLM-focused), AgentLens understands agents: tool calls, handoffs, memory reads, and decision trees — not just LLM generations.

![AgentLens Demo](docs/demo.gif)

<details>
<summary>Screenshots</summary>

### Trace List — search, filter, sort, and compare agent runs
![Trace List](docs/screenshots/01-trace-list.png)

### Agent Topology Graph — visualize tool calls, LLM calls, and handoffs
![Topology Graph](docs/screenshots/02-trace-detail.png)

### Span Detail Panel — inspect any node with input/output, cost, and duration
![Span Detail](docs/screenshots/03-span-detail.png)

</details>

## Features

- **Live trace streaming** — watch your agent think in real-time with incremental span updates
- **Agent topology graph** — visualize agent spawns, tool calls, and handoffs as an interactive DAG
- **Trace comparison** — side-by-side diff of two agent runs with color-coded span matching
- **Search & filters** — full-text search, status/agent/date/cost filters, sortable columns, pagination
- **Cost tracking** — 27 models priced (GPT-4.1, Claude 4, Gemini 2.0, DeepSeek, Llama 3.3)
- **Framework integrations** — LangChain, CrewAI, AutoGen, LlamaIndex, Google ADK
- **OpenTelemetry export** — bridge spans to any OTel-compatible backend
- **OpenTelemetry ingestion** — receive OTLP HTTP JSON spans from any OTel-instrumented app
- **Batch transport** — configurable queue with auto-flush for high-throughput agents
- **Self-hosted** — `docker run` and done. Your data never leaves your machine.
- **90+ tests** — server + SDK with >82% coverage

## Quickstart

```bash
# 1. Start the dashboard
docker run -p 3000:3000 tranhoangtu/agentlens:0.3.0

# 2. Install the SDK (Python or TypeScript)
pip install agentlens-observe   # Python
npm install agentlens-observe   # TypeScript/Node.js
```

```python
# 3a. Instrument your agent (Python)
import agentlens

agentlens.configure(server_url="http://localhost:3000")

@agentlens.trace(name="ResearchAgent")
def run_agent(query: str) -> str:
    with agentlens.span("web_search", "tool_call") as s:
        result = search(query)
        s.set_output(result)
        s.set_cost("gpt-4o", input_tokens=500, output_tokens=200)
    return summarize(result)

run_agent("Latest AI research papers")
# → Traces stream to http://localhost:3000
```

```typescript
// 3b. Instrument your agent (TypeScript)
import * as agentlens from "agentlens-observe";

agentlens.configure({ serverUrl: "http://localhost:3000" });

const result = await agentlens.trace("ResearchAgent", async () => {
  const s = agentlens.span("web_search", "tool_call").enter();
  const data = await search(query);
  s.setOutput(data);
  s.setCost("gpt-4o", { inputTokens: 500, outputTokens: 200 });
  s.exit();
  return summarize(data);
});
```

## How It Works

```
Your Agent (Python/TS)       AgentLens Server          Browser Dashboard
      │                            │                         │
      ├── @agentlens.trace ──────► POST /api/traces ───────► Live topology graph
      │   (fire-and-forget)        │                         │
      │   flush_span() ──────────► POST /api/traces/:id/spans► Real-time node updates
      │                            │                         │
Any OTel App ────────────────────► POST /api/otel/v1/traces ► Same dashboard
      │   (OTLP HTTP JSON)         │                         │
      │                            ├── SSE stream ──────────► span_created events
      │                            │                         │
      └── Never blocked            └── SQLite/PostgreSQL      └── Cost breakdown + diff
```

## Framework Integrations

### LangChain / LangGraph

```python
from agentlens.integrations.langchain import AgentLensCallbackHandler

agent.run("task", callbacks=[AgentLensCallbackHandler()])
```

### CrewAI

```python
from agentlens.integrations.crewai import patch_crewai

patch_crewai()  # Auto-instruments all Crew runs
```

### AutoGen

```python
from agentlens.integrations.autogen import patch_autogen

patch_autogen()  # Patches ConversableAgent.generate_reply
```

### LlamaIndex

```python
from agentlens.integrations.llamaindex import AgentLensCallbackHandler
from llama_index.core import Settings
from llama_index.core.callbacks import CallbackManager

Settings.callback_manager = CallbackManager([AgentLensCallbackHandler()])
```

### Google ADK

```python
from agentlens.integrations.google_adk import patch_google_adk

patch_google_adk()  # Patches Agent.run and tool invocations
```

### OpenTelemetry Export

```python
from agentlens.exporters.otel import AgentLensOTelExporter
agentlens.add_exporter(AgentLensOTelExporter())
```

### OpenTelemetry Ingestion

Any OTel-instrumented app can push spans directly to AgentLens via the OTLP HTTP JSON endpoint:

```bash
# Point your OTel SDK exporter at AgentLens
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:3000/api/otel
export OTEL_EXPORTER_OTLP_PROTOCOL=http/json
```

```python
# Or send spans manually
import requests

requests.post("http://localhost:3000/api/otel/v1/traces", json={
    "resourceSpans": [{
        "resource": {"attributes": [
            {"key": "service.name", "value": {"stringValue": "my-agent"}}
        ]},
        "scopeSpans": [{"spans": [{
            "traceId": "abc123", "spanId": "span001",
            "parentSpanId": "", "name": "agent_run",
            "kind": 2, "startTimeUnixNano": "1700000000000000000",
            "endTimeUnixNano": "1700000001000000000",
            "attributes": [], "status": {"code": 1}
        }]}]
    }]
})
```

Span kind mapping: `SERVER` → `agent_run`, `CLIENT` → `tool_call`, `INTERNAL` → `llm_call`, default → `task`.

## Advanced Usage

### Batch Transport

```python
agentlens.configure(
    server_url="http://localhost:3000",
    batch_size=50,        # flush every 50 traces
    batch_interval=5.0,   # or every 5 seconds
)
```

### Custom Logging

```python
@agentlens.trace(name="MyAgent")
def run():
    agentlens.log("Starting research phase", phase="research")
    # logs appear in span.metadata["logs"]
```

## Development

```bash
# Dashboard (React + Vite)
cd dashboard && npm install && npm run dev

# Server (FastAPI)
cd server && python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --reload --port 8000

# Python SDK
cd sdk && pip install -e ".[dev]"

# TypeScript SDK
cd sdk-ts && npm install && npm test

# Tests
cd server && pytest tests/
cd sdk && pytest tests/
cd sdk-ts && npm test

# PostgreSQL (optional — default is SQLite)
DATABASE_URL=postgresql://user:pass@localhost:5432/agentlens .venv/bin/uvicorn main:app --reload
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Dashboard | React 19, Vite 7, React Flow 12, Tailwind 3, Recharts 3, Radix UI |
| Server | Python FastAPI, SQLite (WAL) / PostgreSQL, SSE |
| Python SDK | Python 3.10+, httpx, OTel bridge |
| TypeScript SDK | Node.js 18+, zero dependencies, AsyncLocalStorage |
| Testing | pytest, httpx, respx (90+ tests, >82% coverage) |

## Roadmap

- [x] ~~Run diff (compare two agent executions)~~
- [x] ~~OpenTelemetry export~~
- [x] ~~Search, filters, pagination~~
- [x] ~~Framework integrations (AutoGen, LlamaIndex, Google ADK)~~
- [x] ~~Replay/time-travel debugging~~
- [x] ~~OpenTelemetry ingestion (receive OTel spans)~~
- [x] ~~PostgreSQL backend~~
- [x] ~~TypeScript SDK~~
- [ ] Alerting on agent behavior anomalies
- [ ] Multi-tenant auth

## License

MIT — see [LICENSE](LICENSE)
