"""LangChain integration: auto-instrument LLM calls and tool calls."""
import logging
import uuid
from typing import Any, Optional

try:
    from langchain_core.callbacks.base import BaseCallbackHandler
    from langchain_core.outputs import LLMResult
except ImportError:
    raise ImportError("langchain-core required: pip install agentlens[langchain]")

from agentlens.tracer import SpanData, _current_trace, _now_ms
from agentlens.cost import calculate_cost

logger = logging.getLogger("agentlens.integrations.langchain")


class AgentLensCallbackHandler(BaseCallbackHandler):
    """Drop-in LangChain callback that records LLM + tool spans into AgentLens."""

    def __init__(self):
        self._llm_starts: dict[str, int] = {}               # run_id -> start_ms
        self._tool_starts: dict[str, tuple[int, str]] = {}  # run_id -> (start_ms, tool_name)

    def _active(self):
        return _current_trace.get()

    def on_llm_start(self, serialized: dict, prompts: list, run_id: Any, **kwargs):
        self._llm_starts[str(run_id)] = _now_ms()

    def on_llm_end(self, response: LLMResult, run_id: Any, **kwargs):
        active = self._active()
        if not active:
            return
        start = self._llm_starts.pop(str(run_id), _now_ms())
        model = kwargs.get("invocation_params", {}).get("model_name", "unknown")
        # Extract token usage from response metadata — schema varies by provider
        usage = {}
        if response.generations and hasattr(response.generations[0][0], "generation_info"):
            gi = response.generations[0][0].generation_info or {}
            usage = gi.get("usage", gi.get("token_usage", {}))
        in_tok = usage.get("prompt_tokens", 0)
        out_tok = usage.get("completion_tokens", 0)
        cost = None
        if in_tok or out_tok:
            usd = calculate_cost(model, in_tok, out_tok)
            cost = {"model": model, "input_tokens": in_tok,
                    "output_tokens": out_tok, "usd": usd}
        output_text = ""
        if response.generations:
            output_text = response.generations[0][0].text[:2048]
        span = SpanData(
            span_id=str(uuid.uuid4()),
            parent_id=active.current_span_id(),
            name=f"llm:{model}",
            type="llm_call",
            start_ms=start,
            end_ms=_now_ms(),
            output=output_text,
            cost=cost,
        )
        active.spans.append(span)

    def on_tool_start(self, serialized: dict, input_str: str, run_id: Any, **kwargs):
        tool_name = serialized.get("name", "unknown_tool")
        self._tool_starts[str(run_id)] = (_now_ms(), tool_name)

    def on_tool_end(self, output: str, run_id: Any, **kwargs):
        active = self._active()
        if not active:
            return
        entry = self._tool_starts.pop(str(run_id), None)
        if not entry:
            return
        start, tool_name = entry
        span = SpanData(
            span_id=str(uuid.uuid4()),
            parent_id=active.current_span_id(),
            name=f"tool:{tool_name}",
            type="tool_call",
            start_ms=start,
            end_ms=_now_ms(),
            output=str(output)[:2048],
        )
        active.spans.append(span)
