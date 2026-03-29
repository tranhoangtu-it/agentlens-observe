"""BYO API key LLM provider — raw HTTP calls to OpenAI, Anthropic, Gemini."""

import json
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 60.0


class LLMProviderError(Exception):
    """Raised when LLM API call fails."""

    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


def call_llm(
    provider: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    json_mode: bool = True,
) -> str:
    """Call an LLM provider and return the text response.

    Args:
        provider: "openai" | "anthropic" | "gemini"
        api_key: User's API key (plaintext)
        model: Model identifier (e.g. "gpt-4o-mini")
        system_prompt: System instructions
        user_prompt: User message
        json_mode: Request JSON-formatted response

    Returns:
        Response text from the LLM.

    Raises:
        LLMProviderError: On API errors or timeouts.
    """
    try:
        if provider == "openai":
            return _call_openai(api_key, model, system_prompt, user_prompt, json_mode)
        elif provider == "anthropic":
            return _call_anthropic(api_key, model, system_prompt, user_prompt)
        elif provider == "gemini":
            return _call_gemini(api_key, model, system_prompt, user_prompt)
        else:
            raise LLMProviderError(f"Unknown provider: {provider}")
    except httpx.TimeoutException:
        raise LLMProviderError("LLM request timed out", status_code=504)
    except httpx.HTTPError as e:
        raise LLMProviderError(f"HTTP error: {e}", status_code=502)


def _call_openai(
    api_key: str, model: str, system: str, user: str, json_mode: bool,
) -> str:
    body: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    with httpx.Client(timeout=_TIMEOUT) as client:
        res = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body,
        )
    if res.status_code != 200:
        raise LLMProviderError(f"OpenAI API error: {res.status_code} {res.text[:200]}", res.status_code)
    return res.json()["choices"][0]["message"]["content"]


def _call_anthropic(api_key: str, model: str, system: str, user: str) -> str:
    # Anthropic doesn't have json_mode — instruct in system prompt
    with httpx.Client(timeout=_TIMEOUT) as client:
        res = client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 4096,
                "system": system,
                "messages": [{"role": "user", "content": user}],
                "temperature": 0.2,
            },
        )
    if res.status_code != 200:
        raise LLMProviderError(f"Anthropic API error: {res.status_code} {res.text[:200]}", res.status_code)
    return res.json()["content"][0]["text"]


def _call_gemini(api_key: str, model: str, system: str, user: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    with httpx.Client(timeout=_TIMEOUT) as client:
        res = client.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "system_instruction": {"parts": [{"text": system}]},
                "contents": [{"parts": [{"text": user}]}],
                "generationConfig": {"temperature": 0.2},
            },
        )
    if res.status_code != 200:
        raise LLMProviderError(f"Gemini API error: {res.status_code} {res.text[:200]}", res.status_code)
    return res.json()["candidates"][0]["content"]["parts"][0]["text"]
