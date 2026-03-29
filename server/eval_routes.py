"""API routes for LLM-as-Judge evaluations."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from auth_deps import get_current_user
from auth_models import User
from eval_models import EvalCriteriaIn, EvalCriteriaUpdate, EvalRunRequest
from eval_runner import run_eval
from eval_storage import (
    create_criteria, list_criteria, get_criteria, update_criteria, delete_criteria,
    create_eval_run, list_eval_runs, get_eval_run, get_score_aggregates,
)
from llm_provider import LLMProviderError
from settings_storage import get_decrypted_api_key, get_settings
from storage import get_trace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/eval", tags=["eval"])


# ── Criteria CRUD ────────────────────────────────────────────────────────────

@router.get("/criteria")
def list_criteria_endpoint(
    agent_name: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
):
    return {"criteria": list_criteria(user.id, agent_name)}


@router.post("/criteria", status_code=201)
def create_criteria_endpoint(body: EvalCriteriaIn, user: User = Depends(get_current_user)):
    if body.score_type not in ("numeric", "binary"):
        raise HTTPException(422, "score_type must be 'numeric' or 'binary'")
    data = body.model_dump()
    data["user_id"] = user.id
    return create_criteria(data)


@router.put("/criteria/{criteria_id}")
def update_criteria_endpoint(
    criteria_id: str, body: EvalCriteriaUpdate, user: User = Depends(get_current_user),
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if "score_type" in data and data["score_type"] not in ("numeric", "binary"):
        raise HTTPException(422, "score_type must be 'numeric' or 'binary'")
    result = update_criteria(criteria_id, data, user.id)
    if not result:
        raise HTTPException(404, "Criteria not found")
    return result


@router.delete("/criteria/{criteria_id}", status_code=204)
def delete_criteria_endpoint(criteria_id: str, user: User = Depends(get_current_user)):
    if not delete_criteria(criteria_id, user.id):
        raise HTTPException(404, "Criteria not found")


# ── Eval execution ───────────────────────────────────────────────────────────

@router.post("/run", status_code=201)
def run_eval_endpoint(body: EvalRunRequest, user: User = Depends(get_current_user)):
    """Run eval criteria against one or more traces."""
    criteria = get_criteria(body.criteria_id, user.id)
    if not criteria:
        raise HTTPException(404, "Criteria not found")

    settings = get_settings(user.id)
    provider = body.provider or (settings.llm_provider if settings else "openai")
    model = body.model or (settings.llm_model if settings else "gpt-4o-mini")
    api_key = get_decrypted_api_key(user.id)
    if not api_key:
        raise HTTPException(422, "No LLM API key configured. Go to Settings.")

    if len(body.trace_ids) > 10:
        raise HTTPException(422, "Max 10 traces per eval run")

    results = []
    errors = []
    for trace_id in body.trace_ids:
        trace_data = get_trace(trace_id, user_id=user.id)
        if not trace_data:
            errors.append({"trace_id": trace_id, "error": "Trace not found"})
            continue
        trace = trace_data["trace"]
        spans = trace_data["spans"]

        try:
            eval_result = run_eval(criteria, trace, spans, provider, api_key, model)
        except LLMProviderError as e:
            logger.error("Eval LLM call failed for trace %s: %s", trace_id, e)
            errors.append({"trace_id": trace_id, "error": "LLM call failed"})
            continue

        # Extract prompt info from span metadata if available
        prompt_name, prompt_version = None, None
        for s in spans:
            if s.metadata_json:
                try:
                    meta = json.loads(s.metadata_json)
                    if "prompt_name" in meta:
                        prompt_name = meta["prompt_name"]
                        prompt_version = meta.get("prompt_version")
                        break
                except (json.JSONDecodeError, TypeError):
                    pass

        run = create_eval_run({
            "criteria_id": criteria.id,
            "trace_id": trace_id,
            "user_id": user.id,
            "score": eval_result["score"],
            "reasoning": eval_result["reasoning"],
            "llm_provider": provider,
            "llm_model": model,
            "prompt_name": prompt_name,
            "prompt_version": prompt_version,
        })
        results.append(run)

    return {"runs": results, "count": len(results), "errors": errors}


# ── Eval runs listing ────────────────────────────────────────────────────────

@router.get("/runs")
def list_runs_endpoint(
    criteria_id: Optional[str] = Query(None),
    trace_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
):
    runs, total = list_eval_runs(user.id, criteria_id, trace_id, limit, offset)
    return {"runs": runs, "total": total, "limit": limit, "offset": offset}


@router.get("/runs/{run_id}")
def get_run_endpoint(run_id: str, user: User = Depends(get_current_user)):
    run = get_eval_run(run_id, user.id)
    if not run:
        raise HTTPException(404, "Eval run not found")
    return run


# ── Score aggregation ────────────────────────────────────────────────────────

@router.get("/scores")
def get_scores_endpoint(
    criteria_id: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
):
    return {"scores": get_score_aggregates(user.id, criteria_id)}
