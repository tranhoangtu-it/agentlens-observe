# agentlens

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Go](https://img.shields.io/badge/Go-00ADD8?style=flat-square&logo=go&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)

Self-hosted observability platform for debugging AI agents. Trace tool calls, inspect decision trees, and monitor agent behavior. An open-source alternative to LangSmith and Langfuse.

## Features

- **Trace & Replay** — Tool call tracing, timeline visualization, time-travel replay with sandbox mode
- **AI Autopsy** — AI-powered failure analysis identifies root causes and suggests fixes (BYO API key)
- **MCP Protocol Tracing** — First-class support for Model Context Protocol tool calls, resource reads, prompt gets
- **Prompt Versioning** — Version-controlled prompt templates with diff comparison
- **LLM-as-Judge Eval** — Automated quality assessment with custom criteria and scoring rubrics
- **Plugin System** — SDK-side SpanProcessors + server-side auto-discovered plugins
- **Alerting** — Rule-based alerts on cost, latency, error rate with webhook notifications
- **Real-time Dashboard** — SSE-powered live updates, topology graphs, cost charts
- **SDKs** — Python and TypeScript with integrations for LangChain, CrewAI, AutoGen, LlamaIndex, Google ADK, MCP
- **CLI Tool** — Go-based CLI for traces list/show/tail/diff and stdin pipe ingestion
- **VS Code Extension** — Sidebar trace tree, detail webview, status bar

## Architecture

```
sdk/                # Python SDK (PyPI: agentlens-observe)
sdk-ts/             # TypeScript SDK (npm: agentlens-observe)
server/             # FastAPI backend (Python)
dashboard/          # React web UI (TypeScript)
cli/                # Go CLI tool
vscode-extension/   # VS Code extension
```

## Quick Start (Docker)

```bash
docker compose up
```

Dashboard available at `http://localhost:3000`

## SDK Installation

**Python**
```bash
pip install agentlens-observe
# With framework integrations:
pip install agentlens-observe[langchain,mcp]
```

**TypeScript**
```bash
npm install agentlens-observe
```

## Usage

```python
from agentlens import AgentLens

lens = AgentLens(endpoint="http://localhost:8000")

with lens.trace("my-agent"):
    lens.log_tool_call("search", {"query": "test"})
```

### MCP Tracing

```python
from agentlens.integrations.mcp import patch_mcp
patch_mcp()  # Auto-instruments all MCP ClientSession calls
```

### CLI

```bash
# Install
cd cli && go build -o agentlens .

# Usage
agentlens config set endpoint http://localhost:8000
agentlens config set api-key al_xxxxx
agentlens traces list --status=error
agentlens traces tail
cat trace.json | agentlens push
```

### VS Code Extension

1. Open `vscode-extension/` in VS Code
2. Press F5 to launch Extension Development Host
3. Configure `agentlens.endpoint` and `agentlens.apiKey` in settings

## Development

```bash
# Server
cd server && pip install -r requirements.txt
uvicorn main:app --reload --port 8000
pytest  # 279+ tests

# Dashboard
cd dashboard && npm install
npm run dev  # Vite dev server, port 5173

# Python SDK
cd sdk && pip install -e ".[dev]"
pytest

# TypeScript SDK
cd sdk-ts && npm install
npm run build && npm run test
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AGENTLENS_DB_PATH` | SQLite file path | `./agentlens.db` |
| `DATABASE_URL` | PostgreSQL connection (overrides SQLite) | — |
| `AGENTLENS_CORS_ORIGINS` | Comma-separated allowed origins | `localhost:3000,localhost:5173` |
| `AGENTLENS_JWT_SECRET` | JWT signing + API key encryption secret | auto-generated (set in production!) |

## License

See [LICENSE](./LICENSE) for details.
