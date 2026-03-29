"""API routes for AI-powered failure autopsy."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException

from auth_deps import get_current_user
from auth_models import User
from autopsy_analyzer import analyze_trace
from autopsy_models import AutopsyOut, AutopsyRequestIn
from autopsy_storage import create_autopsy, delete_autopsy, get_autopsy
from llm_provider import LLMProviderError
from settings_storage import get_decrypted_api_key, get_settings
from storage import get_trace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["autopsy"])


def _autopsy_to_out(result, cached: bool = False) -> AutopsyOut:
    """Convert AutopsyResult DB row to API response."""
    return AutopsyOut(
        id=result.id,
        trace_id=result.trace_id,
        root_cause=result.root_cause,
        summary=result.summary,
        severity=result.severity,
        suggested_fix=result.suggested_fix,
        affected_span_ids=json.loads(result.affected_span_ids_json),
        llm_provider=result.llm_provider,
        llm_model=result.llm_model,
        created_at=result.created_at.isoformat(),
        cached=cached,
    )


@router.post("/traces/{trace_id}/autopsy", status_code=201)
def trigger_autopsy(
    trace_id: str,
    body: AutopsyRequestIn = AutopsyRequestIn(),
    user: User = Depends(get_current_user),
) -> AutopsyOut:
    """Analyze a trace with AI. Returns cached result if available."""
    # Check cache
    cached = get_autopsy(trace_id, user.id)
    if cached:
        return _autopsy_to_out(cached, cached=True)

    # Get user settings
    settings = get_settings(user.id)
    provider = body.provider or (settings.llm_provider if settings else "openai")
    model = body.model or (settings.llm_model if settings else "gpt-4o-mini")

    api_key = get_decrypted_api_key(user.id)
    if not api_key:
        raise HTTPException(
            status_code=422,
            detail="No LLM API key configured. Go to Settings to add your API key.",
        )

    # Get trace + spans
    trace_data = get_trace(trace_id, user_id=user.id)
    if not trace_data:
        raise HTTPException(status_code=404, detail="Trace not found")

    trace = trace_data["trace"]
    spans = trace_data["spans"]

    # Call LLM
    try:
        analysis = analyze_trace(trace, spans, provider, api_key, model)
    except LLMProviderError as e:
        raise HTTPException(status_code=502, detail=f"LLM analysis failed: {e}")

    # Store result
    result = create_autopsy({
        "trace_id": trace_id,
        "user_id": user.id,
        "root_cause": analysis["root_cause"],
        "summary": analysis["summary"],
        "severity": analysis["severity"],
        "suggested_fix": analysis["suggested_fix"],
        "affected_span_ids_json": json.dumps(analysis["affected_span_ids"]),
        "llm_provider": provider,
        "llm_model": model,
    })

    return _autopsy_to_out(result)


@router.get("/traces/{trace_id}/autopsy")
def get_autopsy_endpoint(
    trace_id: str,
    user: User = Depends(get_current_user),
) -> AutopsyOut:
    """Get cached autopsy result for a trace."""
    result = get_autopsy(trace_id, user.id)
    if not result:
        raise HTTPException(status_code=404, detail="No autopsy found for this trace")
    return _autopsy_to_out(result, cached=True)


@router.delete("/traces/{trace_id}/autopsy", status_code=204)
def delete_autopsy_endpoint(
    trace_id: str,
    user: User = Depends(get_current_user),
):
    """Delete cached autopsy to allow re-analysis."""
    deleted = delete_autopsy(trace_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="No autopsy found for this trace")
