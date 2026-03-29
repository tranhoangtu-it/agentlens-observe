# Security Audit Report -- AgentLens Codebase

**Date:** 2026-03-30
**Scope:** Full codebase audit across server, dashboard, Python SDK, Go CLI, VS Code extension, .NET SDK
**Focus:** OWASP Top 10, auth/authz, injection, data leaks, SSRF, credential handling

---

## Critical Issues

### [CRITICAL-01] Default Admin Password in Docker + No Forced Change
**File:** `server/auth_seed.py:15-16`, `docker-compose.yml:11`
**Description:** Default admin password is `changeme` (env) / `admin` (docker-compose). The warning log is easily missed. No mechanism forces a password change on first login. An attacker can access any fresh deployment with `admin@agentlens.local` / `admin`.
**Impact:** Full admin account takeover on any deployment that doesn't set env vars.
**Fix:** Either (a) refuse to start without explicit `AGENTLENS_ADMIN_PASSWORD` in production mode, or (b) generate a random password and print it to stdout once, or (c) require password change on first login.

### [CRITICAL-02] Health Endpoint Leaks Database Error Details
**File:** `server/main.py:82`
**Description:** The `/api/health` endpoint returns the full exception string when DB connection fails: `"db": f"error: {e}"`. This can leak internal hostnames, connection strings, file paths, or driver versions to unauthenticated callers. The health endpoint has no auth requirement.
**Impact:** Information disclosure to unauthenticated attackers; aids reconnaissance.
**Fix:** Return generic `"db": "error"` to callers. Log the full exception server-side only.
```python
except Exception as e:
    logger.error("Health check DB error: %s", e)
    return {"status": "degraded", "db": "error"}
```

### [CRITICAL-03] CORS Allows All Methods and All Headers
**File:** `server/main.py:60-65`
**Description:** `allow_methods=["*"]` and `allow_headers=["*"]` is overly permissive. Combined with configurable origins, this is acceptable for dev, but in production with user-set origins, the wildcard methods/headers expand the attack surface unnecessarily.
**Impact:** Enables preflight bypass for unexpected HTTP methods; exposes application to CORS misconfiguration attacks if origins are loosened.
**Fix:** Restrict to `allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]` and `allow_headers=["Authorization", "Content-Type", "X-API-Key"]`.

---

## High Priority Issues

### [HIGH-01] SDK Transport Sends Traces Without Authentication
**File:** `sdk/agentlens/transport.py` (entire file), `sdk-dotnet/src/AgentLens/Transport.cs` (entire file)
**Description:** Neither the Python nor .NET SDK transport attaches any `Authorization` or `X-API-Key` header to HTTP requests. The server requires authentication on all `/api/traces` endpoints. This means SDK traces will always get 401 unless the user hacks their own headers -- but the SDK API has no parameter for API key.
**Impact:** SDK is effectively broken for authenticated servers; users must disable auth or use workarounds. If auth is disabled to make SDK work, all data is unprotected.
**Fix:** Add `api_key` parameter to `Tracer.configure()` and pass it through to transport. Set `X-API-Key` header on all outgoing requests.
```python
# transport.py
def post_trace(..., api_key: Optional[str] = None):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
```

### [HIGH-02] No Rate Limiting on Login/Register Endpoints
**File:** `server/auth_routes.py:20-39`
**Description:** `/api/auth/login` and `/api/auth/register` have no rate limiting. An attacker can brute-force passwords or spam account creation indefinitely.
**Impact:** Credential brute-force; resource exhaustion via account spam.
**Fix:** Add rate limiting middleware (e.g., `slowapi` for FastAPI) with per-IP limits: ~5 login attempts/minute, ~3 registrations/hour.

### [HIGH-03] No Email Validation on Registration
**File:** `server/auth_routes.py:21-28`, `server/auth_models.py:51-52`
**Description:** `RegisterIn.email` is typed as `str` with no format validation. Users can register with arbitrary strings like `"; DROP TABLE user; --` as email. While SQLModel uses parameterized queries (safe from SQL injection), this allows spam accounts and confusing data.
**Impact:** Data integrity issues; potential phishing if email is displayed in UI without validation.
**Fix:** Add Pydantic `EmailStr` validator:
```python
from pydantic import BaseModel, EmailStr
class RegisterIn(BaseModel):
    email: EmailStr
```

### [HIGH-04] Webhook URL Validation Can Be Bypassed via DNS Rebinding
**File:** `server/alert_notifier.py:31-66`
**Description:** SSRF protection validates the DNS resolution at validation time, but the actual HTTP request (line 108) happens asynchronously in a background thread. Between validation and request, DNS could rebind to a private IP (TOCTOU vulnerability). Also, the URL is validated each time `fire_webhook` is called, but DNS can change between resolve-time and request-time.
**Impact:** SSRF to internal services via DNS rebinding.
**Fix:** Use a custom urllib opener that resolces to IP first, validates, then connects to that specific IP. Or use `httpx` with a custom transport that hooks into resolution.

### [HIGH-05] Password Policy Is Minimal (Length Only)
**File:** `server/auth_routes.py:26`
**Description:** Only check is `len(body.password) < 8`. No complexity requirements, no common password blocklist, no breach check.
**Impact:** Users can set trivially guessable passwords like `password` or `12345678`.
**Fix:** At minimum, check against a small blocklist of top-1000 common passwords. Consider adding complexity hints in the response.

### [HIGH-06] `config set` Echoes API Key in Plaintext to Stdout
**File:** `cli/cmd/config.go:61`
**Description:** `fmt.Fprintf(os.Stdout, "Config updated: %s = %s\n", key, value)` prints the raw API key to terminal when user runs `agentlens config set api-key <key>`. If terminal is logged (CI/CD, screen recording), key is exposed.
**Impact:** Credential leak via terminal history, CI logs, or screen captures.
**Fix:** Mask the value when key is `api-key`:
```go
displayVal := value
if key == "api-key" {
    displayVal = value[:4] + "****"
}
fmt.Fprintf(os.Stdout, "Config updated: %s = %s\n", key, displayVal)
```

---

## Medium Priority Issues

### [MED-01] JWT Secret Auto-Generation Without Persistent Warning
**File:** `server/auth_jwt.py:14-23`
**Description:** When `AGENTLENS_JWT_SECRET` is unset, a random secret is generated. All JWTs become invalid on restart. The warning is logged once at startup but easy to miss. In Docker, restarts are common.
**Impact:** User sessions silently invalidated on server restart; confusing UX. Not a direct vulnerability but enables scenarios where users lower security (e.g., removing auth entirely) to avoid the frustration.
**Fix:** In production mode (detected via env var or flag), refuse to start without explicit JWT secret. Log at ERROR level, not WARNING.

### [MED-02] Encryption Key Derived from JWT Secret
**File:** `server/crypto.py:20-27`
**Description:** The Fernet encryption key for LLM API keys is derived from `AGENTLENS_JWT_SECRET` via SHA-256. This means: (a) JWT secret compromise = LLM API key compromise, (b) changing JWT secret makes all stored LLM keys unrecoverable, (c) the same secret serves two different security purposes.
**Impact:** Single point of failure for both auth tokens and encrypted data at rest.
**Fix:** Use a separate `AGENTLENS_ENCRYPTION_KEY` environment variable for Fernet encryption, independent from JWT secret.

### [MED-03] SSE Bus Has No Authentication on Subscription Filter
**File:** `server/sse.py:19-21`
**Description:** The SSE bus filters by `user_id`, but the filter logic is `if user_id is None or sub_uid is None or sub_uid == user_id`. If `user_id` is `None` on publish (which never happens in current code but is a latent risk), events broadcast to all subscribers. The `get_optional_user` dependency exists but is unused on any current route -- all SSE routes use `get_current_user`.
**Impact:** Low risk currently, but fragile design. A future developer using `user_id=None` on publish would leak events cross-tenant.
**Fix:** Make publish always require a `user_id` parameter (remove the `None` default) or add explicit assertion.

### [MED-04] `setattr()` on SQLModel Objects from User-Controlled Dict Keys
**File:** `server/alert_storage.py:67-68`, `server/settings_storage.py:33-35`
**Description:** `update_alert_rule` and `upsert_settings` iterate over dict keys from user input and call `setattr(rule, key, val)`. While Pydantic models filter unknown fields, if `exclude_unset=True` is used (which it is in `alert_routes.py:63`), the keys come from the Pydantic model. However, if a field like `user_id` or `id` is included in the update model, it would overwrite ownership. `AlertRuleUpdate` does NOT include `user_id` or `id`, so this is safe today but brittle.
**Impact:** Currently safe. Future additions to update models could enable privilege escalation if not carefully reviewed.
**Fix:** Explicitly allowlist updatable fields rather than iterating all dict keys:
```python
_UPDATABLE = {"name", "agent_name", "metric", "operator", "threshold", "mode", "window_size", "enabled", "webhook_url"}
for key, val in data.items():
    if key in _UPDATABLE and val is not None:
        setattr(rule, key, val)
```

### [MED-05] LLM API Error Responses Leak Partial Response Bodies
**File:** `server/llm_provider.py:81,104,121`
**Description:** Error messages include `res.text[:200]` which could contain sensitive data from the LLM provider (error details, account info, partial responses). These propagate to `LLMProviderError` and could reach the client via 502 responses.
**Impact:** Information leakage from third-party API error responses to end users.
**Fix:** Log the full error server-side; return generic error to client. The `autopsy_routes.py` already does this correctly (line 76), but ensure `LLMProviderError` messages don't propagate to HTTP responses elsewhere.

### [MED-06] VS Code Extension API Key Stored in VS Code Settings (Plaintext)
**File:** `vscode-extension/src/config.ts:18-19`
**Description:** API key is read from `vscode.workspace.getConfiguration("agentlens").get("apiKey")`. VS Code settings are stored in plaintext JSON files (`.vscode/settings.json` or user settings). If workspace settings are used, the key may be committed to version control.
**Impact:** API key exposure in git repos or settings sync.
**Fix:** Use VS Code's `SecretStorage` API (`context.secrets.get/store`) for API key storage. Add `.vscode/settings.json` to `.gitignore` template.

### [MED-07] Trace ID Is User-Controlled and Used as Primary Key
**File:** `server/storage.py:78-79`, `server/main.py:89-91`
**Description:** `trace_id` from the request body is used directly as the database primary key. A user can overwrite another user's trace by sending the same `trace_id` (the `create_trace` function does a delete-and-reinsert). However, the `user_id` check in `create_trace` is only applied on read, not on the upsert -- there is NO ownership check before deleting an existing trace.
**Impact:** Any authenticated user can overwrite any other user's trace data by guessing/knowing their trace_id. This is an **IDOR vulnerability**.
**Fix:** Add ownership check before upsert in `create_trace`:
```python
existing = session.get(Trace, trace_id)
if existing:
    if user_id and existing.user_id != user_id:
        raise ValueError("Trace belongs to another user")
    session.execute(text("DELETE FROM span WHERE trace_id = :tid"), {"tid": trace_id})
    session.delete(existing)
```

### [MED-08] No Input Size Limits on Trace/Span Ingestion
**File:** `server/main.py:88-100`, `server/models.py:61-77`
**Description:** There is a 100-span limit per incremental request, but no limit on: (a) number of spans in the initial `TraceIn`, (b) size of `input`/`output` string fields per span, (c) size of `metadata` dict. A malicious SDK user could send a trace with 100,000 spans or spans with 100MB input strings.
**Impact:** Denial of service via storage exhaustion or memory exhaustion during processing.
**Fix:** Add limits: max 500 spans per trace creation, max 64KB per input/output field, max 16KB metadata per span. Validate in `TraceIn` model.

---

## Low Priority Issues

### [LOW-01] `get_optional_user` Exists But Is Unused
**File:** `server/auth_deps.py:51-59`
**Description:** This dependency was designed for "migration period" optional auth but is not used by any route. If a developer uses it for a new route, they'll inadvertently create an unauthenticated endpoint.
**Impact:** Code smell; invitation for future auth bypass.
**Fix:** Remove or mark with a strong deprecation warning.

### [LOW-02] No CSRF Protection on State-Changing Operations
**File:** `dashboard/src/lib/fetch-with-auth.ts`
**Description:** The dashboard uses Bearer tokens in `Authorization` header (not cookies), which inherently protects against CSRF since browsers don't auto-attach custom headers cross-origin. This is correct and safe.
**Impact:** None currently. Noted for completeness -- do not switch to cookie-based auth without adding CSRF tokens.

### [LOW-03] CLI Config File Permissions Are Correct
**File:** `cli/cmd/root.go:80,88`
**Description:** Config directory created with `0700`, config file written with `0600`. This is correct and prevents other users from reading the API key.
**Impact:** None -- this is correctly implemented.

### [LOW-04] Webview Has Scripts Disabled
**File:** `vscode-extension/src/trace-detail-webview.ts:34`
**Description:** `enableScripts: false` is set on the webview panel. All dynamic content uses the `esc()` HTML escape function. This is correct and prevents XSS.
**Impact:** None -- properly secured.

### [LOW-05] Missing `allow_credentials` in CORS
**File:** `server/main.py:60-65`
**Description:** CORS config does not set `allow_credentials=True`. Since auth uses `Authorization` header (not cookies), this is correct. If cookies were needed, this would be a bug.
**Impact:** None currently.

---

## Positive Observations

1. **SQL injection protection**: All DB queries use SQLModel/SQLAlchemy parameterized queries. Sort column injection is prevented with allowlist (`_SORT_COLS` in `storage.py:122`).
2. **Tenant isolation**: All data-access routes filter by `user_id` from JWT. Cross-tenant reads return 404 (not 403) to prevent ID enumeration.
3. **API key hashing**: API keys are stored as SHA-256 hashes with only prefix displayed. Full key returned only at creation time.
4. **Password hashing**: bcrypt with auto-generated salt. Good choice.
5. **SSRF protection**: Webhook URL validation checks DNS resolution against private networks. Blocks `localhost`, RFC-1918, link-local, IPv6 ULA.
6. **HTML escaping in VS Code webview**: All user data is escaped via `esc()` function before rendering. Scripts disabled.
7. **Encrypted API key storage**: LLM API keys encrypted at rest with Fernet (AES-128-CBC + HMAC). Never returned in API responses.
8. **Plugin system validates protocol**: Plugin loader checks `isinstance(plugin, ServerPlugin)` before registration.

---

## Summary Table

| # | Severity | Issue | Component |
|---|----------|-------|-----------|
| CRITICAL-01 | CRITICAL | Default admin password, no forced change | Server |
| CRITICAL-02 | CRITICAL | Health endpoint leaks DB error details | Server |
| CRITICAL-03 | CRITICAL | Overly permissive CORS wildcards | Server |
| HIGH-01 | HIGH | SDK transports have no auth support | Python SDK, .NET SDK |
| HIGH-02 | HIGH | No rate limiting on login/register | Server |
| HIGH-03 | HIGH | No email format validation on registration | Server |
| HIGH-04 | HIGH | SSRF bypass via DNS rebinding (TOCTOU) | Server |
| HIGH-05 | HIGH | Minimal password policy | Server |
| HIGH-06 | HIGH | CLI echoes API key in plaintext | Go CLI |
| MED-01 | MEDIUM | JWT secret auto-generation silently | Server |
| MED-02 | MEDIUM | Encryption key derived from JWT secret | Server |
| MED-03 | MEDIUM | SSE bus broadcast when user_id=None | Server |
| MED-04 | MEDIUM | setattr from user-controlled dict keys | Server |
| MED-05 | MEDIUM | LLM API errors leak response bodies | Server |
| MED-06 | MEDIUM | VS Code stores API key in plaintext settings | VS Code Extension |
| MED-07 | MEDIUM | Trace ID IDOR -- no ownership check on upsert | Server |
| MED-08 | MEDIUM | No input size limits on trace ingestion | Server |

---

## Recommended Priority Order

1. **MED-07** (Trace ID IDOR) -- reclassify to HIGH; any user can overwrite another user's traces
2. **CRITICAL-01** (default admin password) -- immediate fix
3. **CRITICAL-02** (health endpoint info leak) -- quick fix
4. **HIGH-01** (SDK auth) -- SDK is functionally broken without this
5. **HIGH-02** (rate limiting) -- add slowapi or similar
6. **HIGH-06** (CLI key echo) -- quick fix
7. **MED-02** (separate encryption key) -- important for key rotation
8. **MED-08** (input size limits) -- DoS prevention
9. Remaining items per severity order

---

## Unresolved Questions

1. Is there a production deployment guide that instructs users to set `AGENTLENS_JWT_SECRET` and `AGENTLENS_ADMIN_PASSWORD`? If not, CRITICAL-01 is actively exploitable on any Docker deployment.
2. Is the Python SDK intended to work with authenticated servers? If so, HIGH-01 is a functional bug, not just a security concern.
3. Is there a `/api/traces/batch` endpoint? The SDK transport references it (`transport.py:95`) but no such route exists in the server -- batch mode will always 404.
4. Are there plans for multi-tenancy where users should NOT be able to see each other's data? The tenant isolation is implemented but MED-07 breaks it.
