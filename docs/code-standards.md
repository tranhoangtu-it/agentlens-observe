# AgentLens v0.2.0 — Code Standards & Conventions

## File Organization

### Root Structure
```
agentlens/
├── dashboard/          # React SPA (Vite)
├── server/             # FastAPI backend
├── sdk/                # Python SDK
├── scripts/            # Utilities (seed data, screenshots)
├── plans/              # Development plans
├── docs/               # Documentation
├── Dockerfile          # Multi-stage build
├── docker-compose.yml  # Local dev setup
└── README.md
```

### Dashboard (`dashboard/src/`)
```
components/
├── ui/                 # shadcn/ui primitives (badge, button, card, etc.)
├── trace-list-table.tsx            # Virtualized table
├── trace-topology-graph.tsx        # React Flow DAG
├── trace-compare-graphs.tsx        # Dual topology
├── span-detail-panel.tsx           # Detail view
├── span-diff-panel.tsx             # Comparison diff
├── cost-summary-chart.tsx          # Recharts pie
├── trace-search-bar.tsx            # Search input
├── trace-filter-controls.tsx       # Filter dropdowns
└── pagination-controls.tsx         # Page controls

lib/
├── api-client.ts       # Typed API wrapper (fetch)
├── utils.ts            # Helpers (format, parse)
├── use-sse-traces.ts   # EventSource hook
├── use-live-trace-detail.ts        # Real-time updates
├── use-trace-filters.ts            # Filter state
└── diff-utils.ts       # LCS matching, color coding

pages/
├── traces-list-page.tsx            # Trace discovery
├── trace-detail-page.tsx           # Single trace
└── trace-compare-page.tsx          # Comparison (lazy-loaded)

index.css              # Tailwind + custom CSS variables
main.tsx               # React app entry
App.tsx                # Router
```

### Server (`server/`)
```
main.py                # FastAPI app + endpoints
models.py              # SQLModel + Pydantic schemas
storage.py             # SQLite CRUD
sse.py                 # Event bus
diff.py                # LCS diff algorithm

tests/
├── conftest.py        # pytest fixtures
├── test_api_endpoints.py           # Endpoint tests
├── test_sse.py                     # Event bus tests
└── test_storage.py                 # CRUD tests

static/                # Built React app (dist/)
requirements.txt       # Dependencies
```

### SDK (`sdk/agentlens/`)
```
__init__.py            # Public API (v0.2.0)
tracer.py              # Tracer, SpanExporter
transport.py           # HTTPClient, batch queue
cost.py                # Pricing table (27 models)

integrations/
├── __init__.py
├── langchain.py                    # LangChain callback
├── crewai.py                       # CrewAI patch
├── autogen.py                      # AutoGen patch
├── llamaindex.py                   # LlamaIndex callback
└── google_adk.py                   # Google ADK patch

exporters/
├── __init__.py
└── otel.py                         # OTel SpanExporter

tests/
├── conftest.py        # fixtures
├── test_tracer.py                  # Tracer tests
├── test_transport.py               # Transport tests
└── test_cost.py                    # Pricing tests

pyproject.toml         # Dependencies + metadata
README.md              # SDK docs
```

## Naming Conventions

### Python
- **Files:** `kebab-case-with-dashes.py` (e.g., `api-client.ts`, `trace-list-table.tsx`)
- **Classes:** `PascalCase` (e.g., `Tracer`, `Span`)
- **Functions:** `snake_case` (e.g., `create_trace`, `add_spans_to_trace`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `MAX_BATCH_SIZE`, `DEFAULT_INTERVAL`)
- **Private:** Prefix with `_` (e.g., `_validate_trace()`)

### TypeScript/React
- **Files:** `kebab-case.ts(x)` (e.g., `trace-list-table.tsx`, `use-sse-traces.ts`)
- **Components:** `PascalCase` (e.g., `TraceListTable`, `SpanDetailPanel`)
- **Hooks:** `useCamelCase` (e.g., `useSSETraces`, `useTraceFilters`)
- **Types:** `PascalCase` (e.g., `TraceResponse`, `SpanDiff`)
- **Constants:** `camelCase` (e.g., `defaultPageSize`, `retryMaxAttempts`)

### Database
- **Tables:** `PascalCase` (e.g., `Trace`, `Span`)
- **Columns:** `snake_case` (e.g., `agent_name`, `created_at`, `cost_model`)
- **Indexes:** `ix_{table}_{columns}` (e.g., `ix_trace_status_created`)

## Code Style

### Python (Server & SDK)

**Imports**
```python
# 1. Standard library
from datetime import datetime
import json

# 2. Third-party
from fastapi import FastAPI
from sqlmodel import SQLModel

# 3. Local
from models import Trace
from storage import create_trace
```

**Type Hints (Required)**
```python
def list_traces(
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Trace], int]:
    """List traces with optional search and pagination."""
    pass

class Tracer:
    def __init__(self) -> None:
        self._queue: list[Span] = []

    def span(self, name: str, type_: str) -> SpanContext:
        ...
```

**Docstrings**
```python
def compute_diff(left: Trace, right: Trace) -> DiffResult:
    """Compute LCS diff between two trace trees.

    Args:
        left: First trace
        right: Second trace

    Returns:
        DiffResult with matches, insertions, deletions

    Raises:
        ValueError: If traces are empty
    """
    pass
```

**Error Handling**
```python
try:
    trace = create_trace(trace_id, agent_name, spans)
except ValueError as e:
    raise HTTPException(status_code=422, detail=str(e))
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise HTTPException(status_code=500)
```

### TypeScript/React

**Component Structure**
```typescript
import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface TraceListProps {
  traces: Trace[];
  onSelect?: (trace: Trace) => void;
}

export function TraceList({ traces, onSelect }: TraceListProps) {
  return (
    <div className={cn("space-y-2", "p-4")}>
      {traces.map(trace => (
        <div key={trace.id} onClick={() => onSelect?.(trace)}>
          {trace.agent_name}
        </div>
      ))}
    </div>
  );
}
```

**Hook Pattern**
```typescript
export function useSSETraces(traceId: string) {
  const [spans, setSpans] = useState<Span[]>([]);

  useEffect(() => {
    const es = new EventSource(`/api/traces/${traceId}/stream`);
    es.addEventListener("span_created", (event) => {
      setSpans(prev => [...prev, JSON.parse(event.data)]);
    });
    return () => es.close();
  }, [traceId]);

  return spans;
}
```

**Tailwind Classes (Utility-First)**
```typescript
<div className="space-y-4 p-4 bg-slate-900 dark:bg-slate-800 rounded-lg shadow-md">
  <h1 className="text-xl font-semibold text-slate-100">Traces</h1>
  <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-md text-white">
    Export
  </button>
</div>
```

## API Design

### Request/Response Schemas
```python
class SpanIn(BaseModel):
    """Client → Server"""
    span_id: str
    name: str
    type: str  # "llm_call" | "tool_call" | "handoff" | "agent_spawn"
    start_ms: int
    end_ms: Optional[int] = None
    input: Optional[str] = None
    output: Optional[str] = None
    cost: Optional[CostIn] = None
    metadata: Optional[dict] = None

class SpanOut(BaseModel):
    """Server → Client"""
    id: str
    trace_id: str
    name: str
    duration_ms: int
    cost_usd: Optional[float] = None
```

### HTTP Status Codes
- `200` — OK
- `201` — Created (POST /traces, /spans)
- `400` — Bad Request (invalid input)
- `404` — Not Found (trace not found)
- `422` — Unprocessable (validation error)
- `500` — Server Error

### Query Parameters
```
GET /api/traces?q=search&status=running&agent_name=ResearchAgent
  &from_date=2025-02-01T00:00:00&to_date=2025-02-28T23:59:59
  &min_cost=0.01&max_cost=10.0
  &sort=created_at&order=desc
  &limit=50&offset=0
```

## Testing Standards

### Coverage Target: >82%

**Unit Tests (pytest)**
```python
def test_tracer_span_hierarchy():
    tracer = Tracer()
    with tracer.span("parent", "agent_spawn") as parent:
        with tracer.span("child", "tool_call") as child:
            child.set_output("result")

    assert parent.children[0] == child
    assert child.parent_id == parent.id

def test_list_traces_filters_by_status():
    storage.create_trace("t1", "agent1", spans, status="completed")
    storage.create_trace("t2", "agent1", spans, status="running")

    completed, count = storage.list_traces(status="completed")
    assert len(completed) == 1
    assert completed[0].status == "completed"
```

**Integration Tests**
```python
def test_post_traces_endpoint_creates_and_streams(client):
    response = client.post("/api/traces", json={
        "trace_id": "t1",
        "agent_name": "ResearchAgent",
        "spans": [...]
    })
    assert response.status_code == 201
    assert response.json()["trace_id"] == "t1"
```

**Frontend Tests (Vitest)**
```typescript
import { render, screen } from "@testing-library/react";
import { TraceList } from "@/components/trace-list-table";

test("renders trace names", () => {
  render(<TraceList traces={[
    { id: "t1", agent_name: "Agent1", ... }
  ]} />);
  expect(screen.getByText("Agent1")).toBeInTheDocument();
});
```

## Performance Guidelines

### Backend
- API endpoints: P50 <200ms, P99 <500ms
- DB queries: Use compound indexes for filtering
- Batch ingestion: 50-100 spans per POST

### Frontend
- Component render: <16ms (60fps)
- Table scroll: Virtualized (1000+ rows)
- Topology graph: <300ms for 100 nodes
- Code bundle: <1MB (4 chunks)

### SDK
- Transport: Fire-and-forget (non-blocking)
- Batch queue: 50 spans or 5 seconds
- Overhead: <1% of agent runtime

## Security Standards

### CORS
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Dev only; restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Input Validation
```python
class TraceIn(BaseModel):
    trace_id: str  # Required
    agent_name: str  # Required
    spans: list[SpanIn]  # Min 1 span

    @field_validator("trace_id")
    def validate_trace_id(cls, v):
        if not v or len(v) > 255:
            raise ValueError("trace_id must be 1-255 chars")
        return v
```

### Secrets
- Never log passwords, API keys, PII
- Use environment variables for config
- `.env` excluded from git

## Git Workflow

### Commit Messages (Conventional Commits)
```
feat: add trace comparison endpoint
fix: correct span tree traversal in diff
docs: update architecture diagram
test: add >82% coverage target
refactor: simplify batch transport queue
```

### Branch Naming
- Feature: `feature/trace-comparison`
- Fix: `fix/span-indexing-bug`
- Docs: `docs/api-documentation`

## Code Review Checklist

- [ ] Type hints on all functions
- [ ] Docstrings on public methods
- [ ] Error handling (try/catch or raises)
- [ ] Tests included (unit + integration)
- [ ] No hardcoded credentials
- [ ] No console.log() in production code
- [ ] Performance validated (no N+1 queries)
- [ ] Backwards compatible (no breaking changes)
