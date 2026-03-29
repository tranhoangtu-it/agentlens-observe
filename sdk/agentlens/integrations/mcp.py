"""MCP integration: patch ClientSession async methods to emit spans."""
import logging
import uuid

from agentlens.tracer import SpanData, _current_trace, _now_ms

logger = logging.getLogger("agentlens.integrations.mcp")
_patched = False


def patch_mcp():
    """Call once at startup to auto-instrument all MCP ClientSession calls."""
    global _patched
    if _patched:
        return
    try:
        from mcp import ClientSession
        _patch_call_tool(ClientSession)
        _patch_read_resource(ClientSession)
        _patch_get_prompt(ClientSession)
        _patched = True
        logger.info("AgentLens: MCP patched successfully")
    except ImportError:
        raise ImportError("mcp required: pip install agentlens[mcp]")


def _get_server_name(session_self) -> str:
    """Extract MCP server name from session, falling back to 'unknown'."""
    info = getattr(session_self, "server_info", None)
    if info:
        return getattr(info, "name", "unknown")
    return "unknown"


def _patch_call_tool(ClientSession):
    original = ClientSession.call_tool

    async def patched(self, name, arguments=None, **kwargs):
        active = _current_trace.get()
        start = _now_ms()
        result = await original(self, name, arguments, **kwargs)
        if active:
            span = SpanData(
                span_id=str(uuid.uuid4()),
                parent_id=active.current_span_id(),
                name=f"mcp:{name}",
                type="mcp.tool_call",
                start_ms=start,
                end_ms=_now_ms(),
                input=str(arguments)[:1024] if arguments else None,
                output=str(result)[:2048],
                metadata={
                    "mcp_server": _get_server_name(self),
                    "tool_name": name,
                    "arguments": arguments,
                },
            )
            active.spans.append(span)
            active.flush_span(span)
        return result

    ClientSession.call_tool = patched


def _patch_read_resource(ClientSession):
    original = ClientSession.read_resource

    async def patched(self, uri, **kwargs):
        active = _current_trace.get()
        start = _now_ms()
        result = await original(self, uri, **kwargs)
        if active:
            span = SpanData(
                span_id=str(uuid.uuid4()),
                parent_id=active.current_span_id(),
                name=f"mcp:read:{uri}",
                type="mcp.resource_read",
                start_ms=start,
                end_ms=_now_ms(),
                input=str(uri)[:1024],
                output=str(result)[:2048],
                metadata={
                    "mcp_server": _get_server_name(self),
                    "resource_uri": str(uri),
                },
            )
            active.spans.append(span)
            active.flush_span(span)
        return result

    ClientSession.read_resource = patched


def _patch_get_prompt(ClientSession):
    original = ClientSession.get_prompt

    async def patched(self, name, arguments=None, **kwargs):
        active = _current_trace.get()
        start = _now_ms()
        result = await original(self, name, arguments, **kwargs)
        if active:
            span = SpanData(
                span_id=str(uuid.uuid4()),
                parent_id=active.current_span_id(),
                name=f"mcp:prompt:{name}",
                type="mcp.prompt_get",
                start_ms=start,
                end_ms=_now_ms(),
                input=str(arguments)[:1024] if arguments else None,
                output=str(result)[:2048],
                metadata={
                    "mcp_server": _get_server_name(self),
                    "prompt_name": name,
                    "arguments": arguments,
                },
            )
            active.spans.append(span)
            active.flush_span(span)
        return result

    ClientSession.get_prompt = patched
