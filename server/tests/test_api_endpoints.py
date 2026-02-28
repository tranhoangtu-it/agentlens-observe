"""Tests for FastAPI endpoints in main.py."""

import pytest
import uuid


def make_api_trace_data(trace_id=None, agent_name="search_agent"):
    """Generate unique trace data for API testing."""
    uid = str(uuid.uuid4())
    return {
        "trace_id": trace_id or f"trace-{uid}",
        "agent_name": agent_name,
        "spans": [
            {
                "span_id": f"span-1-{uid}",
                "parent_id": None,
                "name": agent_name,
                "type": "agent_run",
                "start_ms": 1000,
                "end_ms": 5000,
                "input": "test input",
                "output": "test output",
                "cost": {
                    "model": "gpt-4o",
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "usd": 0.001,
                },
                "metadata": {"version": "1.0"},
            },
            {
                "span_id": f"span-2-{uid}",
                "parent_id": f"span-1-{uid}",
                "name": "subtask",
                "type": "tool_call",
                "start_ms": 1100,
                "end_ms": 3000,
                "input": "subtask input",
                "output": "subtask output",
                "cost": None,
                "metadata": {},
            },
        ],
    }


class TestHealthEndpoint:
    """Test /api/health."""

    def test_health_endpoint(self, client):
        """Health check returns 200."""
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestIngestTraceEndpoint:
    """Test POST /api/traces."""

    def test_ingest_trace_success(self, client):
        """Post valid trace returns 201."""
        data = make_api_trace_data()
        response = client.post("/api/traces", json=data)
        assert response.status_code == 201
        body = response.json()
        assert body["trace_id"] == data["trace_id"]
        assert body["status"] == "completed"

    def test_ingest_trace_invalid_body(self, client):
        """Invalid body returns 422."""
        response = client.post("/api/traces", json={"invalid": "data"})
        assert response.status_code == 422

    def test_ingest_trace_missing_required_fields(self, client):
        """Missing required fields returns 422."""
        response = client.post(
            "/api/traces",
            json={"trace_id": "test", "agent_name": "agent"},
        )
        assert response.status_code == 422


class TestListTracesEndpoint:
    """Test GET /api/traces."""

    def test_list_traces_default(self, client):
        """Get /api/traces returns paginated list."""
        # Create a few traces
        for i in range(3):
            data = make_api_trace_data(agent_name=f"agent-{i}")
            client.post("/api/traces", json=data)

        response = client.get("/api/traces")
        assert response.status_code == 200
        body = response.json()
        assert "traces" in body
        assert "total" in body
        assert body["total"] >= 3
        assert body["limit"] == 50
        assert body["offset"] == 0

    def test_list_traces_with_pagination(self, client):
        """Pagination parameters work."""
        for i in range(15):
            data = make_api_trace_data()
            client.post("/api/traces", json=data)

        response = client.get("/api/traces?limit=5&offset=0")
        assert response.status_code == 200
        body = response.json()
        assert len(body["traces"]) <= 5

    def test_list_traces_filter_agent_name(self, client):
        """Filter by agent_name query param."""
        target_agent = f"search_agent_{uuid.uuid4()}"
        data1 = make_api_trace_data(agent_name=target_agent)
        client.post("/api/traces", json=data1)

        data2 = make_api_trace_data(agent_name="chat_agent")
        client.post("/api/traces", json=data2)

        response = client.get(f"/api/traces?agent_name={target_agent}")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["traces"][0]["agent_name"] == target_agent

    def test_list_traces_filter_status(self, client):
        """Filter by status query param."""
        data = make_api_trace_data()
        response = client.post("/api/traces", json=data)
        assert response.status_code == 201

        response = client.get("/api/traces?status=completed")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] >= 1

    def test_list_traces_filter_date_range(self, client):
        """Filter by date range query params."""
        data = make_api_trace_data()
        response = client.post("/api/traces", json=data)
        assert response.status_code == 201

        # Filter with valid ISO date
        response = client.get("/api/traces?from_date=2020-01-01T00:00:00")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] >= 1

    def test_list_traces_invalid_date_format(self, client):
        """Invalid date format returns 422."""
        response = client.get("/api/traces?from_date=invalid-date")
        assert response.status_code == 422

    def test_list_traces_filter_cost_range(self, client):
        """Filter by cost range query params."""
        data = make_api_trace_data()
        response = client.post("/api/traces", json=data)
        assert response.status_code == 201

        response = client.get("/api/traces?min_cost=0.0001&max_cost=0.01")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] >= 1


class TestGetTraceEndpoint:
    """Test GET /api/traces/{trace_id}."""

    def test_get_trace_success(self, client):
        """Get existing trace returns 200 with trace and spans."""
        data = make_api_trace_data()
        client.post("/api/traces", json=data)

        response = client.get(f"/api/traces/{data['trace_id']}")
        assert response.status_code == 200
        body = response.json()
        assert body["trace"]["id"] == data["trace_id"]
        assert body["trace"]["agent_name"] == data["agent_name"]
        assert len(body["spans"]) == 2

    def test_get_trace_not_found(self, client):
        """Non-existent trace returns 404."""
        response = client.get(f"/api/traces/nonexistent-{uuid.uuid4()}")
        assert response.status_code == 404
        body = response.json()
        assert "detail" in body


class TestIngestSpansEndpoint:
    """Test POST /api/traces/{trace_id}/spans."""

    def test_ingest_spans_success(self, client):
        """Post spans to existing trace returns 201."""
        # Create initial trace
        data = make_api_trace_data()
        client.post("/api/traces", json=data)

        # Add more spans
        uid = str(uuid.uuid4())
        parent_id = data["spans"][0]["span_id"]
        new_spans = {
            "spans": [
                {
                    "span_id": f"new-span-{uid}",
                    "parent_id": parent_id,
                    "name": "additional",
                    "type": "tool_call",
                    "start_ms": 2000,
                    "end_ms": 3000,
                    "input": None,
                    "output": None,
                    "cost": None,
                    "metadata": {},
                }
            ]
        }
        response = client.post(
            f"/api/traces/{data['trace_id']}/spans",
            json=new_spans,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["trace_id"] == data["trace_id"]
        assert body["new_span_count"] == 1

    def test_ingest_spans_trace_not_found(self, client):
        """Adding spans to non-existent trace returns 404."""
        new_spans = {
            "spans": [
                {
                    "span_id": "span-x",
                    "parent_id": None,
                    "name": "test",
                    "type": "tool_call",
                    "start_ms": 0,
                    "end_ms": 100,
                    "input": None,
                    "output": None,
                    "cost": None,
                    "metadata": {},
                }
            ]
        }
        response = client.post(
            f"/api/traces/nonexistent-{uuid.uuid4()}/spans",
            json=new_spans,
        )
        assert response.status_code == 404

    def test_ingest_spans_too_many(self, client):
        """Posting more than 100 spans returns 422."""
        # Create initial trace
        data = make_api_trace_data()
        client.post("/api/traces", json=data)

        # Try to add 101 spans
        many_spans = {
            "spans": [
                {
                    "span_id": f"span-{i}",
                    "parent_id": None,
                    "name": f"tool-{i}",
                    "type": "tool_call",
                    "start_ms": 1000 + i,
                    "end_ms": 2000 + i,
                    "input": None,
                    "output": None,
                    "cost": None,
                    "metadata": {},
                }
                for i in range(101)
            ]
        }
        response = client.post(
            f"/api/traces/{data['trace_id']}/spans",
            json=many_spans,
        )
        assert response.status_code == 422


class TestListAgentsEndpoint:
    """Test GET /api/agents."""

    def test_list_agents_success(self, client):
        """Get /api/agents returns distinct agent names."""
        # Create traces with different agents
        for agent in ["search_agent", "chat_agent", "search_agent"]:
            data = make_api_trace_data(agent_name=agent)
            client.post("/api/traces", json=data)

        response = client.get("/api/agents")
        assert response.status_code == 200
        body = response.json()
        assert "agents" in body
        assert "search_agent" in body["agents"]
        assert "chat_agent" in body["agents"]
