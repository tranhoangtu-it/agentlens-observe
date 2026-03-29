"""Tests for MCP integration: patch_mcp idempotency, span creation, no-trace safety."""

import asyncio
import sys
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers — build a fake mcp.ClientSession without requiring the mcp package
# ---------------------------------------------------------------------------

def _make_fake_client_session():
    """Return a minimal fake ClientSession class that mimics mcp.ClientSession."""

    class FakeClientSession:
        async def call_tool(self, name, arguments=None, **kwargs):
            return f"tool_result:{name}"

        async def read_resource(self, uri, **kwargs):
            return f"resource_result:{uri}"

        async def get_prompt(self, name, arguments=None, **kwargs):
            return f"prompt_result:{name}"

    return FakeClientSession


def _inject_fake_mcp(fake_session_cls):
    """Inject a fake `mcp` module into sys.modules so patch_mcp can import it."""
    fake_mcp = MagicMock()
    fake_mcp.ClientSession = fake_session_cls
    sys.modules.setdefault("mcp", fake_mcp)
    return fake_mcp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_patch_state():
    """Reset _patched flag and sys.modules between tests to keep isolation."""
    import agentlens.integrations.mcp as mcp_mod
    original_patched = mcp_mod._patched
    # Store original sys.modules state
    mcp_in_modules = sys.modules.get("mcp")
    yield
    # Restore _patched flag
    mcp_mod._patched = original_patched
    # Restore sys.modules
    if mcp_in_modules is None:
        sys.modules.pop("mcp", None)
    else:
        sys.modules["mcp"] = mcp_in_modules


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPatchMcpIdempotent:
    """patch_mcp() called multiple times must be a no-op after the first call."""

    def test_patch_mcp_idempotent(self):
        import agentlens.integrations.mcp as mcp_mod

        FakeSession = _make_fake_client_session()
        _inject_fake_mcp(FakeSession)

        original_call_tool = FakeSession.call_tool

        mcp_mod._patched = False
        mcp_mod.patch_mcp()
        patched_once = FakeSession.call_tool

        # Second call should not re-wrap
        mcp_mod.patch_mcp()
        assert FakeSession.call_tool is patched_once, (
            "Second patch_mcp() must not re-wrap the method"
        )


class TestToolCallSpanCreated:
    """call_tool inside an active trace must produce a span with correct fields."""

    def test_tool_call_span_created(self):
        import agentlens.integrations.mcp as mcp_mod
        from agentlens.tracer import ActiveTrace, _current_trace

        FakeSession = _make_fake_client_session()
        _inject_fake_mcp(FakeSession)

        mcp_mod._patched = False
        mcp_mod.patch_mcp()

        session = FakeSession()
        session.server_info = SimpleNamespace(name="my-mcp-server")

        active = ActiveTrace(trace_id=str(uuid.uuid4()), agent_name="test_agent")
        token = _current_trace.set(active)
        try:
            result = asyncio.run(session.call_tool("search", {"query": "test"}))
        finally:
            _current_trace.reset(token)

        assert result == "tool_result:search"
        assert len(active.spans) == 1

        span = active.spans[0]
        assert span.type == "mcp.tool_call"
        assert span.name == "mcp:search"
        assert span.metadata["tool_name"] == "search"
        assert span.metadata["mcp_server"] == "my-mcp-server"
        assert span.start_ms > 0
        assert span.end_ms is not None and span.end_ms >= span.start_ms

    def test_read_resource_span_created(self):
        import agentlens.integrations.mcp as mcp_mod
        from agentlens.tracer import ActiveTrace, _current_trace

        FakeSession = _make_fake_client_session()
        _inject_fake_mcp(FakeSession)

        mcp_mod._patched = False
        mcp_mod.patch_mcp()

        session = FakeSession()

        active = ActiveTrace(trace_id=str(uuid.uuid4()), agent_name="test_agent")
        token = _current_trace.set(active)
        try:
            result = asyncio.run(session.read_resource("file:///data.txt"))
        finally:
            _current_trace.reset(token)

        assert result == "resource_result:file:///data.txt"
        assert len(active.spans) == 1

        span = active.spans[0]
        assert span.type == "mcp.resource_read"
        assert span.name == "mcp:read:file:///data.txt"
        assert span.metadata["resource_uri"] == "file:///data.txt"

    def test_get_prompt_span_created(self):
        import agentlens.integrations.mcp as mcp_mod
        from agentlens.tracer import ActiveTrace, _current_trace

        FakeSession = _make_fake_client_session()
        _inject_fake_mcp(FakeSession)

        mcp_mod._patched = False
        mcp_mod.patch_mcp()

        session = FakeSession()

        active = ActiveTrace(trace_id=str(uuid.uuid4()), agent_name="test_agent")
        token = _current_trace.set(active)
        try:
            result = asyncio.run(session.get_prompt("summarize", {"lang": "en"}))
        finally:
            _current_trace.reset(token)

        assert result == "prompt_result:summarize"
        assert len(active.spans) == 1

        span = active.spans[0]
        assert span.type == "mcp.prompt_get"
        assert span.name == "mcp:prompt:summarize"
        assert span.metadata["prompt_name"] == "summarize"


class TestNoActiveTrace:
    """Calling patched methods outside a trace context must not raise."""

    def test_call_tool_no_active_trace_does_not_crash(self):
        import agentlens.integrations.mcp as mcp_mod
        from agentlens.tracer import _current_trace

        FakeSession = _make_fake_client_session()
        _inject_fake_mcp(FakeSession)

        mcp_mod._patched = False
        mcp_mod.patch_mcp()

        # Ensure no active trace
        assert _current_trace.get() is None

        session = FakeSession()
        # Must not raise
        result = asyncio.run(session.call_tool("ping"))
        assert result == "tool_result:ping"

    def test_read_resource_no_crash_standalone(self):
        import agentlens.integrations.mcp as mcp_mod
        from agentlens.tracer import _current_trace

        FakeSession = _make_fake_client_session()
        _inject_fake_mcp(FakeSession)

        mcp_mod._patched = False
        mcp_mod.patch_mcp()

        assert _current_trace.get() is None
        session = FakeSession()
        result = asyncio.run(session.read_resource("mem://buf"))
        assert result == "resource_result:mem://buf"

    def test_get_prompt_no_active_trace_does_not_crash(self):
        import agentlens.integrations.mcp as mcp_mod
        from agentlens.tracer import _current_trace

        FakeSession = _make_fake_client_session()
        _inject_fake_mcp(FakeSession)

        mcp_mod._patched = False
        mcp_mod.patch_mcp()

        assert _current_trace.get() is None
        session = FakeSession()
        result = asyncio.run(session.get_prompt("explain"))
        assert result == "prompt_result:explain"


class TestServerNameFallback:
    """Server name extraction falls back to 'unknown' when server_info absent."""

    def test_unknown_server_name_when_no_server_info(self):
        import agentlens.integrations.mcp as mcp_mod
        from agentlens.tracer import ActiveTrace, _current_trace

        FakeSession = _make_fake_client_session()
        _inject_fake_mcp(FakeSession)

        mcp_mod._patched = False
        mcp_mod.patch_mcp()

        session = FakeSession()
        # No server_info attribute set

        active = ActiveTrace(trace_id=str(uuid.uuid4()), agent_name="test_agent")
        token = _current_trace.set(active)
        try:
            asyncio.run(session.call_tool("noop"))
        finally:
            _current_trace.reset(token)

        assert active.spans[0].metadata["mcp_server"] == "unknown"
