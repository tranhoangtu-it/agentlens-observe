"""Build structured prompts from trace data and parse LLM autopsy responses."""

import json
import logging
from typing import Optional

from models import Span, Trace
from llm_provider import call_llm, LLMProviderError

logger = logging.getLogger(__name__)

_MAX_SPANS = 50
_MAX_IO_CHARS = 500

_SYSTEM_PROMPT = """You are an AI agent debugging expert. Analyze the provided trace data and identify why the agent failed or performed poorly.

Respond ONLY with valid JSON in this exact format:
{
  "root_cause": "Clear explanation of the root cause",
  "summary": "One-sentence summary of the issue",
  "severity": "critical|warning|info",
  "suggested_fix": "Actionable steps to fix the issue",
  "affected_span_ids": ["span-id-1", "span-id-2"]
}

Severity guidelines:
- critical: Agent crashed, produced wrong output, or caused data loss
- warning: Agent was slow, costly, or had retries that succeeded
- info: Minor inefficiency or suboptimal behavior"""


def _build_user_prompt(trace: Trace, spans: list[Span]) -> str:
    """Build a structured prompt from trace and span data."""
    lines = [
        f"## Trace: {trace.id}",
        f"Agent: {trace.agent_name}",
        f"Status: {trace.status}",
        f"Duration: {trace.duration_ms}ms" if trace.duration_ms else "",
        f"Total cost: ${trace.total_cost_usd:.4f}" if trace.total_cost_usd else "",
        f"Span count: {trace.span_count}",
        "",
        "## Spans (chronological):",
    ]

    # Limit to _MAX_SPANS, prioritize error spans and root spans
    selected = spans[:_MAX_SPANS]
    if len(spans) > _MAX_SPANS:
        lines.append(f"(showing {_MAX_SPANS} of {len(spans)} spans)")

    for s in selected:
        duration = f"{s.end_ms - s.start_ms}ms" if s.end_ms and s.start_ms else "?"
        parts = [
            f"- [{s.type}] {s.name} (id={s.id}, duration={duration})",
        ]
        if s.parent_id:
            parts.append(f"  parent: {s.parent_id}")
        if s.input:
            truncated = s.input[:_MAX_IO_CHARS]
            parts.append(f"  input: {truncated}")
        if s.output:
            truncated = s.output[:_MAX_IO_CHARS]
            parts.append(f"  output: {truncated}")
        if s.cost_usd:
            parts.append(f"  cost: ${s.cost_usd:.4f} ({s.cost_model}, {s.cost_input_tokens}in/{s.cost_output_tokens}out)")
        if s.metadata_json:
            parts.append(f"  metadata: {s.metadata_json[:200]}")
        lines.extend(parts)

    return "\n".join(line for line in lines if line is not None)


def analyze_trace(
    trace: Trace,
    spans: list[Span],
    provider: str,
    api_key: str,
    model: str,
) -> dict:
    """Analyze a trace using an LLM and return structured autopsy data.

    Returns dict with: root_cause, summary, severity, suggested_fix, affected_span_ids
    Raises LLMProviderError on failure.
    """
    user_prompt = _build_user_prompt(trace, spans)
    response_text = call_llm(
        provider=provider,
        api_key=api_key,
        model=model,
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        json_mode=(provider == "openai"),
    )

    # Parse JSON response, with fallback for malformed output
    try:
        # Strip markdown code fences if present
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        data = json.loads(cleaned)
        return {
            "root_cause": str(data.get("root_cause", "Unknown")),
            "summary": str(data.get("summary", "Analysis complete")),
            "severity": data.get("severity", "info") if data.get("severity") in ("critical", "warning", "info") else "info",
            "suggested_fix": str(data.get("suggested_fix", "No specific fix suggested")),
            "affected_span_ids": data.get("affected_span_ids", []),
        }
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("Failed to parse LLM autopsy response as JSON: %s", e)
        return {
            "root_cause": response_text[:2000],
            "summary": "LLM returned non-JSON response — showing raw analysis",
            "severity": "info",
            "suggested_fix": "Review the root cause analysis above",
            "affected_span_ids": [],
        }
