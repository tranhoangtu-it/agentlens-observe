# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is AgentLens

Self-hosted observability platform for debugging AI agents. Traces tool calls, inspects decision trees, monitors agent behavior. Open-source alternative to LangSmith/Langfuse.

## Architecture

Monorepo with 6 packages:

- **server/** — FastAPI backend (Python 3.11+), SQLite default / PostgreSQL via `DATABASE_URL`. SQLModel ORM, JWT auth, SSE real-time, server-side plugins.
- **dashboard/** — React 19 + TypeScript SPA. Vite, Tailwind CSS, React Flow for topology graphs, Recharts for cost charts.
- **sdk/** — Python SDK (`agentlens-observe` on PyPI). Framework integrations: LangChain, CrewAI, AutoGen, LlamaIndex, Google ADK, MCP, OpenTelemetry. SpanProcessor plugin hooks.
- **sdk-ts/** — TypeScript SDK (`agentlens-observe` on npm). Built with tsup, dual CJS/ESM. MCP integration.
- **cli/** — Go CLI tool (Cobra). `traces list/show/tail/diff`, `push` (stdin pipe), `config`.
- **vscode-extension/** — VS Code extension. Sidebar TreeView, WebView detail panel, status bar.

### Data Flow

SDK → `POST /api/traces` or `/api/traces/{id}/spans` → SQLModel storage → SSE bus → Dashboard.
Also: OTLP HTTP at `/api/otel/v1/traces`, server plugins notified on trace create/complete.

### Server Modules by Feature

| Feature | Models | Storage | Routes | Other |
|---------|--------|---------|--------|-------|
| Traces | `models.py` | `storage.py` | `main.py` | `sse.py`, `diff.py`, `otel_mapper.py` |
| Auth | `auth_models.py` | `auth_storage.py` | `auth_routes.py` | `auth_jwt.py`, `auth_deps.py`, `auth_seed.py` |
| Alerts | `alert_models.py` | `alert_storage.py` | `alert_routes.py` | `alert_evaluator.py`, `alert_notifier.py` |
| Settings | `settings_models.py` | `settings_storage.py` | `settings_routes.py` | `crypto.py` |
| Autopsy | `autopsy_models.py` | `autopsy_storage.py` | `autopsy_routes.py` | `autopsy_analyzer.py`, `llm_provider.py` |
| Prompts | `prompt_models.py` | `prompt_storage.py` | `prompt_routes.py` | — |
| Eval | `eval_models.py` | `eval_storage.py` | `eval_routes.py` | `eval_runner.py` |
| Replay | `replay_models.py` | `replay_storage.py` | `replay_routes.py` | — |
| Plugins | `plugin_protocol.py` | — | — | `plugin_loader.py`, `plugins/` |

## Common Commands

### Server
```bash
cd server
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
pytest                          # all tests (~279)
pytest tests/test_storage.py    # single file
pytest -k test_create_trace     # single test
```

### Dashboard
```bash
cd dashboard
npm install
npm run dev         # Vite dev server, port 5173
npm run build       # production build
npm run lint        # ESLint
```

### Python SDK
```bash
cd sdk
pip install -e ".[dev]"
pytest
```

### TypeScript SDK
```bash
cd sdk-ts
npm install
npm run build       # tsup
npm run test        # vitest
npm run typecheck   # tsc --noEmit
```

### Go CLI
```bash
cd cli
go build -o agentlens .
./agentlens --help
```

### VS Code Extension
```bash
cd vscode-extension
npm install
npx tsc -p ./      # compile
# Press F5 in VS Code to launch Extension Development Host
```

### Docker (full stack)
```bash
docker compose up   # dashboard at localhost:3000
```

## Key Design Decisions

- **Tenant isolation**: All queries filter by `user_id` from JWT. `get_current_user` dependency on every endpoint.
- **SSE bus** (sse.py): In-memory pub/sub scoped per user for real-time trace/span events.
- **Server plugins**: Auto-discovered from `server/plugins/` at startup. Protocol: `on_trace_created`, `on_trace_completed`, `register_routes`.
- **SDK plugins**: `SpanProcessor` protocol (on_start/on_end) + `SpanExporter` protocol (export_span/shutdown). Registered via `add_processor()`/`add_exporter()`.
- **BYO API key**: User stores LLM API key encrypted (Fernet via `AGENTLENS_JWT_SECRET`). Used for Autopsy + Eval. Supports OpenAI, Anthropic, Gemini via raw HTTP in `llm_provider.py`.
- **MCP integration**: Monkey-patch on `mcp.ClientSession` (Python) and `@modelcontextprotocol/sdk` Client (TypeScript). Span types: `mcp.tool_call`, `mcp.resource_read`, `mcp.prompt_get`.
- **Prompt versioning**: Immutable versions with auto-increment. `difflib.unified_diff` for comparison.
- **Eval scoring**: Numeric (1-5) and binary (pass/fail). LLM judge with custom rubrics.

## Environment Variables

- `AGENTLENS_DB_PATH` — SQLite file path (default: `./agentlens.db`)
- `DATABASE_URL` — PostgreSQL connection string (overrides SQLite)
- `AGENTLENS_CORS_ORIGINS` — Comma-separated allowed origins (default: `localhost:3000,localhost:5173`)
- `AGENTLENS_JWT_SECRET` — JWT signing + API key encryption secret (**required in production**)

## Adding New Features

Pattern for new server features: create `{feature}_models.py`, `{feature}_storage.py`, `{feature}_routes.py`. Register router in `main.py`. Import models in `tests/conftest.py` for table creation. Follow `alert_*.py` as canonical example.

SDK integrations: Add file in `sdk/agentlens/integrations/`. Follow `crewai.py` (sync) or `mcp.py` (async) pattern. Monkey-patch framework methods, create SpanData, push to active trace.

Dashboard pages: Add route to `App.tsx` Route union + `parseHash()` + NavItem + page render. Follow existing pattern.
