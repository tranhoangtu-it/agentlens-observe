"""Tests for FastAPI endpoints in main.py."""

import asyncio
import threading
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
        data = response.json()
        assert data["status"] == "ok"
        assert data["db"] == "connected"


class TestIngestTraceEndpoint:
    """Test POST /api/traces."""

    def test_ingest_trace_success(self, client, auth_headers):
        """Post valid trace returns 201."""
        data = make_api_trace_data()
        response = client.post("/api/traces", json=data, headers=auth_headers)
        assert response.status_code == 201
        body = response.json()
        assert body["trace_id"] == data["trace_id"]
        assert body["status"] == "completed"

    def test_ingest_trace_invalid_body(self, client, auth_headers):
        """Invalid body returns 422."""
        response = client.post("/api/traces", json={"invalid": "data"}, headers=auth_headers)
        assert response.status_code == 422

    def test_ingest_trace_missing_required_fields(self, client, auth_headers):
        """Missing required fields returns 422."""
        response = client.post(
            "/api/traces",
            json={"trace_id": "test", "agent_name": "agent"},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestListTracesEndpoint:
    """Test GET /api/traces."""

    def test_list_traces_default(self, client, auth_headers):
        """Get /api/traces returns paginated list."""
        for i in range(3):
            data = make_api_trace_data(agent_name=f"agent-{i}")
            client.post("/api/traces", json=data, headers=auth_headers)

        response = client.get("/api/traces", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert "traces" in body
        assert "total" in body
        assert body["total"] >= 3
        assert body["limit"] == 50
        assert body["offset"] == 0

    def test_list_traces_with_pagination(self, client, auth_headers):
        """Pagination parameters work."""
        for i in range(15):
            data = make_api_trace_data()
            client.post("/api/traces", json=data, headers=auth_headers)

        response = client.get("/api/traces?limit=5&offset=0", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert len(body["traces"]) <= 5

    def test_list_traces_filter_agent_name(self, client, auth_headers):
        """Filter by agent_name query param."""
        target_agent = f"search_agent_{uuid.uuid4()}"
        data1 = make_api_trace_data(agent_name=target_agent)
        client.post("/api/traces", json=data1, headers=auth_headers)

        data2 = make_api_trace_data(agent_name="chat_agent")
        client.post("/api/traces", json=data2, headers=auth_headers)

        response = client.get(f"/api/traces?agent_name={target_agent}", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["traces"][0]["agent_name"] == target_agent

    def test_list_traces_filter_status(self, client, auth_headers):
        """Filter by status query param."""
        data = make_api_trace_data()
        response = client.post("/api/traces", json=data, headers=auth_headers)
        assert response.status_code == 201

        response = client.get("/api/traces?status=completed", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["total"] >= 1

    def test_list_traces_filter_date_range(self, client, auth_headers):
        """Filter by date range query params."""
        data = make_api_trace_data()
        response = client.post("/api/traces", json=data, headers=auth_headers)
        assert response.status_code == 201

        response = client.get("/api/traces?from_date=2020-01-01T00:00:00", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["total"] >= 1

    def test_list_traces_invalid_date_format(self, client, auth_headers):
        """Invalid date format returns 422."""
        response = client.get("/api/traces?from_date=invalid-date", headers=auth_headers)
        assert response.status_code == 422

    def test_list_traces_filter_cost_range(self, client, auth_headers):
        """Filter by cost range query params."""
        data = make_api_trace_data()
        response = client.post("/api/traces", json=data, headers=auth_headers)
        assert response.status_code == 201

        response = client.get("/api/traces?min_cost=0.0001&max_cost=0.01", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["total"] >= 1


class TestGetTraceEndpoint:
    """Test GET /api/traces/{trace_id}."""

    def test_get_trace_success(self, client, auth_headers):
        """Get existing trace returns 200 with trace and spans."""
        data = make_api_trace_data()
        client.post("/api/traces", json=data, headers=auth_headers)

        response = client.get(f"/api/traces/{data['trace_id']}", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["trace"]["id"] == data["trace_id"]
        assert body["trace"]["agent_name"] == data["agent_name"]
        assert len(body["spans"]) == 2

    def test_get_trace_not_found(self, client, auth_headers):
        """Non-existent trace returns 404."""
        response = client.get(f"/api/traces/nonexistent-{uuid.uuid4()}", headers=auth_headers)
        assert response.status_code == 404
        body = response.json()
        assert "detail" in body


class TestIngestSpansEndpoint:
    """Test POST /api/traces/{trace_id}/spans."""

    def test_ingest_spans_success(self, client, auth_headers):
        """Post spans to existing trace returns 201."""
        data = make_api_trace_data()
        client.post("/api/traces", json=data, headers=auth_headers)

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
            headers=auth_headers,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["trace_id"] == data["trace_id"]
        assert body["new_span_count"] == 1

    def test_ingest_spans_trace_not_found(self, client, auth_headers):
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
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_ingest_spans_too_many(self, client, auth_headers):
        """Posting more than 100 spans returns 422."""
        data = make_api_trace_data()
        client.post("/api/traces", json=data, headers=auth_headers)

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
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestListAgentsEndpoint:
    """Test GET /api/agents."""

    def test_list_agents_success(self, client, auth_headers):
        """Get /api/agents returns distinct agent names."""
        for agent in ["search_agent", "chat_agent", "search_agent"]:
            data = make_api_trace_data(agent_name=agent)
            client.post("/api/traces", json=data, headers=auth_headers)

        response = client.get("/api/agents", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert "agents" in body
        assert "search_agent" in body["agents"]
        assert "chat_agent" in body["agents"]


class TestCompareTracesEndpoint:
    """Test GET /api/traces/compare."""

    def test_compare_traces_success(self, client, auth_headers):
        """GET /api/traces/compare returns diff for two valid traces."""
        left = make_api_trace_data(agent_name="agent_left")
        right = make_api_trace_data(agent_name="agent_right")
        client.post("/api/traces", json=left, headers=auth_headers)
        client.post("/api/traces", json=right, headers=auth_headers)

        response = client.get(
            f"/api/traces/compare?left={left['trace_id']}&right={right['trace_id']}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert "left" in body
        assert "right" in body
        assert "diff" in body

    def test_compare_traces_not_found(self, client, auth_headers):
        """GET /api/traces/compare with missing trace returns 404."""
        response = client.get(
            f"/api/traces/compare?left=no-such-trace-{uuid.uuid4()}&right=also-missing-{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestStreamTracesEndpoint:
    """Test GET /api/traces/stream SSE endpoint."""

    def test_stream_traces_unauthenticated(self, client):
        """GET /api/traces/stream without auth returns 401 or 403."""
        resp = client.get("/api/traces/stream")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_stream_traces_authenticated_returns_sse(self, client, auth_headers):
        """GET /api/traces/stream with auth returns 200 text/event-stream.

        Patches bus.subscribe to yield one event then stop, so the streaming
        response completes and httpx can read status + content-type.
        """
        import httpx
        from unittest.mock import patch, AsyncMock
        from main import app as fastapi_app

        async def _one_event_generator(user_id=None):
            yield "event: trace_created\ndata: {}\n\n"

        with patch("main.bus.subscribe", side_effect=_one_event_generator):
            transport = httpx.ASGITransport(app=fastapi_app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
                async with ac.stream("GET", "/api/traces/stream", headers=auth_headers) as resp:
                    assert resp.status_code == 200
                    assert "text/event-stream" in resp.headers.get("content-type", "")
                    chunks = []
                    async for chunk in resp.aiter_bytes():
                        chunks.append(chunk)
                    assert len(chunks) > 0


class TestLifespan:
    """Cover main.py lifespan context manager (lines 27-29)."""

    @pytest.mark.asyncio
    async def test_lifespan_calls_init_db_and_seed_admin(self, test_db):
        """lifespan() calls init_db() and seed_admin() then yields (covers lines 27-29)."""
        from unittest.mock import patch, call
        from main import app, lifespan

        # Patch both side-effect functions so lifespan body is executed without real DB init
        with patch("main.init_db") as mock_init_db, \
             patch("main.seed_admin") as mock_seed_admin:
            async with lifespan(app):
                # Inside the context — startup has run
                mock_init_db.assert_called_once()
                mock_seed_admin.assert_called_once()
            # After the context — shutdown has run (yield returned)
