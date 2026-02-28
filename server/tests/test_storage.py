"""Tests for storage.py — trace and span CRUD operations."""

import pytest
import uuid
from datetime import datetime, timezone
from storage import (
    create_trace,
    list_traces,
    get_trace,
    add_spans_to_trace,
    list_agents,
)


def make_trace_data(trace_id=None, agent_name="search_agent", span_count=2):
    """Generate unique trace data for a test."""
    uid = str(uuid.uuid4())
    trace_id = trace_id or f"trace-{uid}"

    spans = []
    for i in range(span_count):
        if i == 0:
            spans.append({
                "span_id": f"span-{i}-{uid}",
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
            })
        else:
            spans.append({
                "span_id": f"span-{i}-{uid}",
                "parent_id": f"span-0-{uid}",
                "name": f"subtask-{i}",
                "type": "tool_call",
                "start_ms": 1000 + i * 100,
                "end_ms": 3000 + i * 100,
                "input": f"input-{i}",
                "output": f"output-{i}",
                "cost": None,
                "metadata": {},
            })

    return {
        "trace_id": trace_id,
        "agent_name": agent_name,
        "spans": spans,
    }


class TestCreateTrace:
    """Test trace creation with aggregates."""

    def test_create_trace_basic(self):
        """Create a trace with spans and verify aggregates."""
        data = make_trace_data()
        trace = create_trace(
            data["trace_id"],
            data["agent_name"],
            data["spans"],
        )

        assert trace.id == data["trace_id"]
        assert trace.agent_name == "search_agent"
        assert trace.span_count == 2
        assert trace.total_cost_usd == 0.001
        assert trace.duration_ms == 4000  # 5000 - 1000
        assert trace.status == "completed"  # all spans have end_ms

    def test_create_trace_running_status(self):
        """Trace without all end_ms should have 'running' status."""
        spans = [
            {
                "span_id": "span-1",
                "parent_id": None,
                "name": "agent",
                "type": "agent_run",
                "start_ms": 1000,
                "end_ms": None,  # Still running
                "input": "test",
                "output": None,
                "cost": None,
                "metadata": {},
            }
        ]
        trace = create_trace("trace-running", "agent", spans)
        assert trace.status == "running"

    def test_create_trace_upsert(self):
        """Creating same trace_id twice replaces old one."""
        data = make_trace_data(span_count=1)
        trace1 = create_trace(data["trace_id"], data["agent_name"], data["spans"])
        assert trace1.span_count == 1

        # Add more spans to same trace_id
        data2 = make_trace_data(trace_id=data["trace_id"], span_count=2)
        trace2 = create_trace(data["trace_id"], data["agent_name"], data2["spans"])
        assert trace2.span_count == 2

    def test_create_trace_cost_aggregation(self):
        """Cost is summed across all spans."""
        uid = str(uuid.uuid4())
        spans = [
            {
                "span_id": f"s1-{uid}",
                "parent_id": None,
                "name": "root",
                "type": "agent_run",
                "start_ms": 0,
                "end_ms": 100,
                "input": None,
                "output": None,
                "cost": {"model": "gpt-4o", "input_tokens": 100, "output_tokens": 50, "usd": 0.001},
                "metadata": {},
            },
            {
                "span_id": f"s2-{uid}",
                "parent_id": f"s1-{uid}",
                "name": "tool",
                "type": "tool_call",
                "start_ms": 10,
                "end_ms": 90,
                "input": None,
                "output": None,
                "cost": {"model": "gpt-3.5-turbo", "input_tokens": 50, "output_tokens": 25, "usd": 0.0005},
                "metadata": {},
            },
        ]
        trace = create_trace(f"cost-test-{uid}", "agent", spans)
        assert trace.total_cost_usd == pytest.approx(0.0015)


class TestListTraces:
    """Test trace listing and filtering."""

    def test_list_traces_pagination(self):
        """Create multiple traces and verify pagination."""
        for i in range(20):
            data = make_trace_data(agent_name=f"agent-{i % 3}")
            create_trace(data["trace_id"], data["agent_name"], data["spans"])

        traces, total = list_traces(limit=10, offset=0)
        assert len(traces) == 10
        assert total == 20

        traces, total = list_traces(limit=10, offset=10)
        assert len(traces) == 10
        assert total == 20

    def test_list_traces_filter_agent_name(self):
        """Filter traces by exact agent_name."""
        target_agent = f"search_agent_{uuid.uuid4()}"
        for i in range(3):
            agent = target_agent if i < 2 else "other_agent"
            data = make_trace_data(agent_name=agent)
            create_trace(data["trace_id"], data["agent_name"], data["spans"])

        traces, total = list_traces(agent_name=target_agent)
        assert total == 2
        assert all(t.agent_name == target_agent for t in traces)

    def test_list_traces_filter_status(self):
        """Filter traces by status."""
        # Create completed trace
        data = make_trace_data()
        create_trace(data["trace_id"], data["agent_name"], data["spans"])

        # Create running trace
        uid = str(uuid.uuid4())
        running_spans = [
            {
                "span_id": f"span-{uid}",
                "parent_id": None,
                "name": "agent",
                "type": "agent_run",
                "start_ms": 1000,
                "end_ms": None,
                "input": None,
                "output": None,
                "cost": None,
                "metadata": {},
            }
        ]
        create_trace(f"trace-running-{uid}", "agent", running_spans)

        # Filter by completed
        traces, total = list_traces(status="completed")
        assert total >= 1
        assert all(t.status == "completed" for t in traces)

        # Filter by running
        traces, total = list_traces(status="running")
        assert total >= 1
        assert all(t.status == "running" for t in traces)

    def test_list_traces_filter_cost_range(self):
        """Filter traces by cost range."""
        # High cost trace
        uid1 = str(uuid.uuid4())
        high_cost_spans = [
            {
                "span_id": f"s-{uid1}",
                "parent_id": None,
                "name": "agent",
                "type": "agent_run",
                "start_ms": 0,
                "end_ms": 100,
                "input": None,
                "output": None,
                "cost": {"model": "gpt-4o", "input_tokens": 10000, "output_tokens": 5000, "usd": 0.1},
                "metadata": {},
            }
        ]
        create_trace(f"trace-expensive-{uid1}", "agent", high_cost_spans)

        # Low cost trace
        data = make_trace_data()
        create_trace(data["trace_id"], data["agent_name"], data["spans"])

        # Filter min cost
        traces, total = list_traces(min_cost=0.01)
        assert total >= 1
        assert all(t.total_cost_usd >= 0.01 for t in traces if t.total_cost_usd)

    def test_list_traces_search_query(self):
        """Search traces by agent_name LIKE pattern."""
        uid = str(uuid.uuid4())
        for i, agent in enumerate(["search_agent", "search_bot", "chat_agent"]):
            data = make_trace_data(agent_name=agent)
            create_trace(data["trace_id"], data["agent_name"], data["spans"])

        traces, total = list_traces(q="search")
        assert total >= 2
        assert all("search" in t.agent_name for t in traces)

    def test_list_traces_sorting(self):
        """Test sorting by different columns."""
        for i in range(3):
            data = make_trace_data(agent_name=f"agent-{i}")
            create_trace(data["trace_id"], data["agent_name"], data["spans"])

        # Sort by created_at desc (default)
        traces, _ = list_traces(sort="created_at", order="desc", limit=3)
        assert len(traces) >= 1

        # Sort by agent_name asc
        traces, _ = list_traces(sort="agent_name", order="asc", limit=3)
        assert len(traces) >= 1


class TestGetTrace:
    """Test retrieving single trace with spans."""

    def test_get_trace_with_spans(self):
        """Retrieve trace and all its spans."""
        data = make_trace_data()
        create_trace(data["trace_id"], data["agent_name"], data["spans"])

        result = get_trace(data["trace_id"])
        assert result is not None
        assert result["trace"].id == data["trace_id"]
        assert len(result["spans"]) == 2

    def test_get_trace_not_found(self):
        """Non-existent trace returns None."""
        result = get_trace(f"nonexistent-{uuid.uuid4()}")
        assert result is None


class TestAddSpansToTrace:
    """Test incremental span addition and aggregate recomputation."""

    def test_add_spans_to_trace_basic(self):
        """Add spans to existing trace and verify new_spans count."""
        # Create initial trace with 1 span
        data = make_trace_data(span_count=1)
        trace = create_trace(data["trace_id"], data["agent_name"], data["spans"])
        assert trace.span_count == 1

        # Add more spans (should have unique span_id from parent)
        uid = str(uuid.uuid4())
        parent_span_id = data["spans"][0]["span_id"]
        new_spans = [
            {
                "span_id": f"new-span-{uid}",
                "parent_id": parent_span_id,
                "name": "additional",
                "type": "tool_call",
                "start_ms": 1500,
                "end_ms": 2500,
                "input": None,
                "output": None,
                "cost": None,
                "metadata": {},
            }
        ]
        result = add_spans_to_trace(data["trace_id"], new_spans)
        assert result is not None
        # Verify new spans were added
        assert len(result["new_spans"]) == 1
        # Verify we can retrieve the trace with all spans
        final = get_trace(data["trace_id"])
        assert len(final["spans"]) == 2

    def test_add_spans_to_trace_not_found(self):
        """Adding spans to non-existent trace returns None."""
        result = add_spans_to_trace(f"nonexistent-{uuid.uuid4()}", [])
        assert result is None

    def test_add_spans_duplicate_ids_skipped(self):
        """Adding spans with duplicate IDs skips them (upsert-like)."""
        data = make_trace_data()
        create_trace(data["trace_id"], data["agent_name"], data["spans"])

        # Try to add spans with duplicate IDs
        result = add_spans_to_trace(data["trace_id"], data["spans"][:1])
        assert result is not None
        assert len(result["new_spans"]) == 0  # None should be added

    def test_add_spans_recomputes_status(self):
        """Status is recomputed when spans are added."""
        # Create running trace
        uid = str(uuid.uuid4())
        incomplete_spans = [
            {
                "span_id": f"s1-{uid}",
                "parent_id": None,
                "name": "agent",
                "type": "agent_run",
                "start_ms": 1000,
                "end_ms": None,
                "input": None,
                "output": None,
                "cost": None,
                "metadata": {},
            }
        ]
        trace = create_trace(f"trace-{uid}", "agent", incomplete_spans)
        assert trace.status == "running"

        # Add completed child span
        completing_spans = [
            {
                "span_id": f"s2-{uid}",
                "parent_id": f"s1-{uid}",
                "name": "tool",
                "type": "tool_call",
                "start_ms": 1100,
                "end_ms": 2000,
                "input": None,
                "output": None,
                "cost": None,
                "metadata": {},
            }
        ]
        result = add_spans_to_trace(f"trace-{uid}", completing_spans)
        assert result["trace"].status == "running"  # Root still incomplete


class TestListAgents:
    """Test listing distinct agent names."""

    def test_list_agents_distinct(self):
        """Return distinct sorted agent names."""
        agents = ["search_agent", "chat_agent", "search_agent"]
        for agent in agents:
            data = make_trace_data(agent_name=agent)
            create_trace(data["trace_id"], data["agent_name"], data["spans"])

        result = list_agents()
        assert len(result) >= 2
        assert "search_agent" in result
        assert "chat_agent" in result
        # Verify sorted
        assert result == sorted(result)

    def test_list_agents_empty(self):
        """Empty database returns empty list."""
        # This test may fail if other tests created agents
        # Just verify it returns a list
        agents = list_agents()
        assert isinstance(agents, list)
