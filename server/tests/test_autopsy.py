"""Tests for autopsy endpoints and LLM provider."""

import json
from unittest.mock import patch


# ── Autopsy endpoints ────────────────────────────────────────────────────────


def _setup_trace_and_key(client, auth_headers, sample_trace_data):
    """Helper: create a trace and configure an API key."""
    client.post("/api/traces", headers=auth_headers, json=sample_trace_data)
    client.put("/api/settings", headers=auth_headers, json={
        "llm_provider": "openai",
        "llm_api_key": "sk-test-key",
        "llm_model": "gpt-4o-mini",
    })
    return sample_trace_data["trace_id"]


_MOCK_LLM_RESPONSE = json.dumps({
    "root_cause": "The search tool returned empty results",
    "summary": "Search tool failure due to invalid query",
    "severity": "warning",
    "suggested_fix": "Add input validation before calling search",
    "affected_span_ids": ["span-1"],
})


def test_autopsy_no_api_key(client, auth_headers, sample_trace_data):
    """POST autopsy without API key configured returns 422."""
    client.post("/api/traces", headers=auth_headers, json=sample_trace_data)
    res = client.post(
        f"/api/traces/{sample_trace_data['trace_id']}/autopsy",
        headers=auth_headers,
    )
    assert res.status_code == 422
    assert "API key" in res.json()["detail"]


def test_autopsy_trace_not_found(client, auth_headers):
    """POST autopsy for nonexistent trace returns 404."""
    client.put("/api/settings", headers=auth_headers, json={
        "llm_provider": "openai",
        "llm_api_key": "sk-test",
        "llm_model": "gpt-4o-mini",
    })
    res = client.post("/api/traces/nonexistent/autopsy", headers=auth_headers)
    assert res.status_code == 404


@patch("autopsy_analyzer.call_llm", return_value=_MOCK_LLM_RESPONSE)
def test_autopsy_trigger(mock_llm, client, auth_headers, sample_trace_data):
    """POST autopsy triggers analysis and returns result."""
    trace_id = _setup_trace_and_key(client, auth_headers, sample_trace_data)
    res = client.post(f"/api/traces/{trace_id}/autopsy", headers=auth_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["root_cause"] == "The search tool returned empty results"
    assert data["severity"] == "warning"
    assert data["cached"] is False
    mock_llm.assert_called_once()


@patch("autopsy_analyzer.call_llm", return_value=_MOCK_LLM_RESPONSE)
def test_autopsy_cached(mock_llm, client, auth_headers, sample_trace_data):
    """Second POST returns cached result without calling LLM again."""
    trace_id = _setup_trace_and_key(client, auth_headers, sample_trace_data)
    client.post(f"/api/traces/{trace_id}/autopsy", headers=auth_headers)
    res2 = client.post(f"/api/traces/{trace_id}/autopsy", headers=auth_headers)
    assert res2.status_code == 201
    assert res2.json()["cached"] is True
    assert mock_llm.call_count == 1  # only called once


@patch("autopsy_analyzer.call_llm", return_value=_MOCK_LLM_RESPONSE)
def test_autopsy_get(mock_llm, client, auth_headers, sample_trace_data):
    """GET autopsy returns cached result."""
    trace_id = _setup_trace_and_key(client, auth_headers, sample_trace_data)
    client.post(f"/api/traces/{trace_id}/autopsy", headers=auth_headers)
    res = client.get(f"/api/traces/{trace_id}/autopsy", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["cached"] is True


def test_autopsy_get_not_found(client, auth_headers, sample_trace_data):
    """GET autopsy for trace without autopsy returns 404."""
    client.post("/api/traces", headers=auth_headers, json=sample_trace_data)
    res = client.get(
        f"/api/traces/{sample_trace_data['trace_id']}/autopsy",
        headers=auth_headers,
    )
    assert res.status_code == 404


@patch("autopsy_analyzer.call_llm", return_value=_MOCK_LLM_RESPONSE)
def test_autopsy_delete(mock_llm, client, auth_headers, sample_trace_data):
    """DELETE autopsy removes cache, allowing re-analysis."""
    trace_id = _setup_trace_and_key(client, auth_headers, sample_trace_data)
    client.post(f"/api/traces/{trace_id}/autopsy", headers=auth_headers)
    res = client.delete(f"/api/traces/{trace_id}/autopsy", headers=auth_headers)
    assert res.status_code == 204
    # Verify cache is gone
    res2 = client.get(f"/api/traces/{trace_id}/autopsy", headers=auth_headers)
    assert res2.status_code == 404


# ── LLM provider unit tests ─────────────────────────────────────────────────


@patch("llm_provider.httpx.Client")
def test_llm_provider_openai(mock_client_cls):
    """Verify OpenAI request format."""
    from llm_provider import call_llm

    mock_response = type("R", (), {"status_code": 200, "json": lambda self: {
        "choices": [{"message": {"content": "test response"}}]
    }})()
    mock_client = mock_client_cls.return_value.__enter__.return_value
    mock_client.post.return_value = mock_response

    result = call_llm("openai", "sk-test", "gpt-4o", "system", "user")
    assert result == "test response"
    call_args = mock_client.post.call_args
    assert "api.openai.com" in call_args[0][0]
    body = call_args[1]["json"]
    assert body["model"] == "gpt-4o"
    assert body["response_format"] == {"type": "json_object"}


@patch("llm_provider.httpx.Client")
def test_llm_provider_anthropic(mock_client_cls):
    """Verify Anthropic request format."""
    from llm_provider import call_llm

    mock_response = type("R", (), {"status_code": 200, "json": lambda self: {
        "content": [{"text": "claude response"}]
    }})()
    mock_client = mock_client_cls.return_value.__enter__.return_value
    mock_client.post.return_value = mock_response

    result = call_llm("anthropic", "sk-ant", "claude-sonnet-4-20250514", "system", "user")
    assert result == "claude response"
    call_args = mock_client.post.call_args
    assert "api.anthropic.com" in call_args[0][0]
    headers = call_args[1]["headers"]
    assert headers["x-api-key"] == "sk-ant"


@patch("llm_provider.httpx.Client")
def test_llm_provider_error(mock_client_cls):
    """Verify error handling on non-200 response."""
    from llm_provider import call_llm, LLMProviderError

    mock_response = type("R", (), {"status_code": 401, "text": "Unauthorized"})()
    mock_client = mock_client_cls.return_value.__enter__.return_value
    mock_client.post.return_value = mock_response

    try:
        call_llm("openai", "bad-key", "gpt-4o", "system", "user")
        assert False, "Should have raised"
    except LLMProviderError as e:
        assert e.status_code == 401
