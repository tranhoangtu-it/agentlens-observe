# Tester Agent Memory — AgentLens

## Project: AgentLens
Path: `/Users/tranhoangtu/Desktop/PET/my-project/agentlens/`

### Stack
- Dashboard: React 19 + Vite 7 + TypeScript 5.9 + Tailwind v3 + @xyflow/react + Recharts
- Server: FastAPI + SQLModel + SQLite (WAL) + SSE, Python 3.14 venv at `server/.venv/`
- SDK: Pure Python (httpx only dep), at `sdk/agentlens/`

### Test Suite Complete (Phase 6 - 2026-02-28)
**Server**: 38 tests, 82% coverage
- Storage CRUD: 18 tests (trace create, list with filters, get, add spans)
- API endpoints: 17 tests (health, ingest, list, get, agents)
- SSE transport: 3 tests (publish/subscribe, multiple subscribers)

**SDK**: 52 tests, >85% coverage
- Tracer: 18 tests (sync/async decorator, spans, nesting, context)
- Cost: 15 tests (known models, edge cases, pricing validation)
- Transport: 19 tests (server URL, post trace/spans, batch mode, threading)

**Test Infrastructure**:
- Server: fresh in-memory SQLite per test via conftest.py fixture
- SDK: respx.mock for httpx + httpx.Response mocking
- All tests deterministic, non-dependent, no external network calls

### Test Commands
```bash
# Server tests
cd /Users/tranhoangtu/Desktop/PET/my-project/agentlens/server && \
  .venv/bin/python -m pytest tests/ -v [--cov=. --cov-report=term-missing]

# SDK tests
cd /Users/tranhoangtu/Desktop/PET/my-project/agentlens/sdk && \
  /path/to/server/.venv/bin/python -m pytest tests/ -v
```

### Known Issues from Testing
1. **storage.py span_count bug** (low): add_spans_to_trace() double-counts spans
2. **datetime.utcnow() deprecation** (medium): Use datetime.now(datetime.UTC)
3. **diff.py untested** (19% coverage): Phase 4 feature — tests deferred

### Testing Patterns (Reusable)
- In-memory SQLite: create_engine + SQLModel.metadata.create_all + text("PRAGMA journal_mode=WAL")
- Unique test data: uuid4 per test to avoid ID collisions
- HTTP mocking: respx.mock context + httpx.Response(status_code)
- Test fixtures: conftest.py with autouse=True for setup/teardown
- Async support: @pytest.mark.asyncio with pytest-asyncio

### Environment Notes
- Bash blocked on .venv — use absolute paths always
- Report: `/Users/tranhoangtu/Desktop/PET/my-project/plans/reports/tester-260228-1255-testing-suite.md`
- Test files: `/Users/tranhoangtu/Desktop/PET/my-project/agentlens/{server,sdk}/tests/`
- No relative paths in responses
- No emojis
- No colons before tool calls
