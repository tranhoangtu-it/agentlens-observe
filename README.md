# AgentLens

**Debug AI agents visually** — self-hosted, open-source, agent-native observability.

> Unlike LangSmith (paid, cloud-only) and Langfuse (LLM-focused), AgentLens understands agents: tool calls, handoffs, memory reads, and decision trees — not just LLM generations.

![AgentLens Demo](docs/demo.gif)

<details>
<summary>📸 Screenshots</summary>

### Trace List — see all agent runs at a glance
![Trace List](docs/screenshots/01-trace-list.png)

### Agent Topology Graph — visualize tool calls, LLM calls, and handoffs
![Topology Graph](docs/screenshots/02-trace-detail.png)

### Span Detail Panel — inspect any node with input/output, cost, and duration
![Span Detail](docs/screenshots/03-span-detail.png)

</details>

## Features

- **Live trace streaming** — watch your agent think in real-time
- **Agent topology graph** — visualize agent spawns, tool calls, and handoffs as an interactive DAG
- **Cost tracking** — token usage + USD per agent run, per span
- **Framework-agnostic** — works with LangChain, CrewAI, AutoGen, or any custom agent
- **Self-hosted** — `docker run` and done. Your data never leaves your machine.
- **Python SDK** — 2-line integration with decorator + context manager API

## Quickstart

```bash
# 1. Start the dashboard
docker run -p 3000:3000 tranhoangtu/agentlens

# 2. Install the SDK
pip install agentlens-observe
```

```python
# 3. Instrument your agent
import agentlens

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

## How It Works

```
Your Agent (Python)          AgentLens Server          Browser Dashboard
      │                            │                         │
      ├── @agentlens.trace ──────► POST /api/traces ───────► Live topology graph
      │   (fire-and-forget)        │                         │
      │                            ├── SSE stream ──────────► Real-time updates
      │                            │                         │
      └── Never blocked            └── SQLite (self-hosted)  └── Cost breakdown
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

## Development

```bash
# Dashboard (React + Vite)
cd dashboard && npm install && npm run dev

# Server (FastAPI)
cd server && python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --reload --port 8000

# SDK
cd sdk && pip install -e .
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Dashboard | React + Vite + React Flow + Tailwind |
| Server | Python FastAPI + SQLite |
| Real-time | Server-Sent Events (SSE) |
| SDK | Python (decorator + context manager) |

## Roadmap

- [ ] Replay/time-travel debugging
- [ ] Run diff (compare two agent executions)
- [ ] OpenTelemetry ingestion
- [ ] PostgreSQL backend
- [ ] TypeScript SDK
- [ ] Alerting on agent behavior anomalies

## License

MIT — see [LICENSE](LICENSE)
