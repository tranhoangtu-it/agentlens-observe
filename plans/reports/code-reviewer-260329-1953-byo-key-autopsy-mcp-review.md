---
type: code-review
date: 2026-03-29
scope: BYO API Key, AI Failure Autopsy, MCP Protocol Tracing
commit: HEAD (latest)
---

# Code Review: BYO API Key + AI Autopsy + MCP Tracing

## Scope

- **Files reviewed**: 11 new files across server/, sdk/, sdk-ts/
- **Features**: BYO API Key Settings, AI Failure Autopsy, MCP Protocol Tracing
- **Focus**: Security, error handling, correctness, code quality

## Overall Assessment

Solid implementation. Clean separation of concerns, proper auth on all endpoints, API keys never returned in responses. A few issues need attention, one critical.

---

## Critical Issues

### [CRITICAL] Gemini API key leaked in URL query parameter
**File**: `server/llm_provider.py:109`
```python
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
```
The Gemini API key is passed as a URL query parameter. This means:
- The key appears in HTTP access logs (reverse proxies, load balancers, CDNs)
- The key may appear in httpx debug/error logs
- Any exception traceback containing `url` leaks the key

**Fix**: Use `x-goog-api-key` header instead:
```python
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
res = client.post(
    url,
    headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
    json={...},
)
```

### [CRITICAL] Hardcoded fallback encryption key in production path
**File**: `server/crypto.py:23`
```python
secret = _jwt_secret or "agentlens-dev-fallback-key"
```
When `AGENTLENS_JWT_SECRET` is unset, all API keys are encrypted with a publicly known static key. The warning at line 14 logs but does NOT prevent encryption. Any attacker who reads the DB file can decrypt all stored API keys.

**Fix**: Refuse to encrypt/decrypt when no secret is configured, or at minimum, block the settings endpoint from accepting API keys when the secret is missing:
```python
def encrypt_value(plaintext: str) -> str:
    if not _jwt_secret:
        raise RuntimeError("AGENTLENS_JWT_SECRET must be set to store API keys")
    return _get_fernet().encrypt(plaintext.encode()).decode()
```

---

## Warning Issues

### [WARNING] LLM error messages may leak API error details to frontend
**File**: `server/autopsy_routes.py:75`
```python
raise HTTPException(status_code=502, detail=f"LLM analysis failed: {e}")
```
The `LLMProviderError` message at `llm_provider.py:81` includes `res.text[:200]` from the LLM API response. This could contain error messages mentioning the API key, account info, or internal error details. Truncation to 200 chars reduces but doesn't eliminate the risk.

**Fix**: Return a generic message to the client, log the full error server-side:
```python
except LLMProviderError as e:
    logger.error("LLM analysis failed for trace %s: %s", trace_id, e)
    raise HTTPException(status_code=502, detail="LLM analysis failed. Check server logs.")
```

### [WARNING] No validation on `model` field — arbitrary model strings passed to LLM APIs
**File**: `server/settings_routes.py:42`, `server/autopsy_routes.py:54`

The `llm_model` field accepts any string. While the LLM API will reject invalid models, an attacker could use this to:
- Probe for available models on the user's API key
- Potentially trigger unexpected billing (e.g., `o1-preview` vs `gpt-4o-mini`)

**Fix**: Add a model allowlist per provider or at least validate the format.

### [WARNING] `affected_span_ids` not validated — LLM can return arbitrary span IDs
**File**: `server/autopsy_analyzer.py:110`
```python
"affected_span_ids": data.get("affected_span_ids", []),
```
The LLM response is trusted to provide valid span IDs. These IDs are stored in DB and returned to the frontend. If the LLM hallucinates span IDs, the frontend may try to highlight non-existent spans.

**Fix**: Validate against actual span IDs from the trace:
```python
valid_ids = {s.id for s in spans}
"affected_span_ids": [sid for sid in data.get("affected_span_ids", []) if sid in valid_ids],
```

### [WARNING] Race condition on autopsy cache — concurrent POST creates duplicates
**File**: `server/autopsy_routes.py:47-88`

Two concurrent POST requests for the same trace_id + user_id will both pass the cache check (line 47), both call the LLM, and both insert into the DB. The `ix_autopsy_trace_user` index is not unique, so duplicates accumulate.

**Fix**: Add a unique constraint on `(trace_id, user_id)` in `AutopsyResult`, or use `INSERT ... ON CONFLICT` / a DB-level lock.

### [WARNING] MCP monkey-patch swallows exceptions silently when no active trace
**File**: `sdk/agentlens/integrations/mcp.py:39-60`

If the patched method raises an exception, the span is never recorded (the `if active:` block is after `await original(...)`). This is correct for not crashing, but the exception propagation path is fine. However, if the original method succeeds but `flush_span` raises, the exception will bubble up and break the user's MCP call. The `flush_span` path should be try/except guarded.

**Fix**: Wrap span creation/flush in try/except:
```python
if active:
    try:
        span = SpanData(...)
        active.spans.append(span)
        active.flush_span(span)
    except Exception:
        logger.debug("Failed to record MCP span", exc_info=True)
```
This applies to both Python `mcp.py` and TypeScript `mcp.ts`.

---

## Info Issues

### [INFO] `_jwt_secret` read at module load — env var changes after import have no effect
**File**: `server/crypto.py:12`

The `AGENTLENS_JWT_SECRET` is read once at import time. This is fine for production (env vars shouldn't change), but means test fixtures that set the env var after import won't affect encryption. Consistent with standard practice, just noting.

### [INFO] Synchronous `httpx.Client` in async FastAPI route
**File**: `server/llm_provider.py:74,87,110`

`call_llm` uses synchronous `httpx.Client` but is called from a FastAPI route that could be async. FastAPI runs sync handlers in a threadpool, so this works, but blocks a threadpool thread for up to 60s during LLM calls. Consider `httpx.AsyncClient` if concurrency becomes a concern.

### [INFO] No rate limiting on autopsy endpoint
**File**: `server/autopsy_routes.py:39`

Each autopsy POST triggers an LLM API call using the user's key. No rate limiting means a user (or attacker with stolen JWT) can burn through API credits rapidly. Low priority since it's the user's own key.

### [INFO] MCP TypeScript uses `eval('require')` for dynamic import
**File**: `sdk-ts/src/integrations/mcp.ts:80`
```typescript
Client = eval('require')("@modelcontextprotocol/sdk/client/index.js").Client;
```
This works for CommonJS but will fail in pure ESM environments. The biome-ignore comment acknowledges this. Consider `await import()` with a sync wrapper pattern, or document the CJS requirement.

### [INFO] Autopsy code fence stripping is fragile
**File**: `server/autopsy_analyzer.py:98-101`

The markdown fence stripping handles `\`\`\`json\n...\`\`\`` but not `\`\`\` json` (space before language tag) or nested fences. Edge case — most LLMs format correctly, but worth noting.

---

## Positive Observations

- API keys never returned in any response (`SettingsOut` only has `llm_api_key_set: bool`)
- All endpoints properly use `Depends(get_current_user)` for auth
- Autopsy caching scoped to `(trace_id, user_id)` prevents cross-tenant data access
- `get_trace()` in storage.py properly checks `user_id` ownership (line 194)
- Provider validation uses a set (`VALID_PROVIDERS`) — clean pattern
- MCP patching is idempotent (`_patched` flag)
- Consistent truncation of span I/O data (1024/2048 chars)
- Good error fallback in autopsy analyzer when LLM returns non-JSON

## Recommended Actions (Priority Order)

1. **[CRITICAL]** Move Gemini API key from URL to header
2. **[CRITICAL]** Block encryption when `AGENTLENS_JWT_SECRET` is unset, or fail the settings PUT endpoint
3. **[WARNING]** Sanitize LLM error messages before returning to client
4. **[WARNING]** Add unique constraint on `(trace_id, user_id)` in `autopsy_result` table
5. **[WARNING]** Wrap MCP span flush in try/except in both Python and TS SDKs
6. **[WARNING]** Validate `affected_span_ids` against actual trace spans

---

**Status:** DONE
**Summary:** 2 critical security issues (Gemini key in URL, hardcoded fallback encryption key), 5 warnings (error leak, race condition, unvalidated LLM output, missing flush guard, model validation). Core architecture is sound.
