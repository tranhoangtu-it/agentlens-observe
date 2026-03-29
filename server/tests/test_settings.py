"""Tests for user LLM settings endpoints and crypto helpers."""

from crypto import encrypt_value, decrypt_value


# ── Crypto roundtrip ─────────────────────────────────────────────────────────

def test_crypto_roundtrip():
    plaintext = "sk-test-key-1234567890"
    encrypted = encrypt_value(plaintext)
    assert encrypted != plaintext
    assert decrypt_value(encrypted) == plaintext


def test_crypto_decrypt_invalid():
    assert decrypt_value("not-valid-ciphertext") is None


# ── GET /api/settings (empty) ────────────────────────────────────────────────

def test_get_settings_empty(client, auth_headers):
    res = client.get("/api/settings", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["llm_provider"] == "openai"
    assert data["llm_api_key_set"] is False
    assert data["llm_model"] == "gpt-4o-mini"


# ── PUT /api/settings ────────────────────────────────────────────────────────

def test_put_settings(client, auth_headers):
    res = client.put("/api/settings", headers=auth_headers, json={
        "llm_provider": "anthropic",
        "llm_api_key": "sk-ant-test-key",
        "llm_model": "claude-sonnet-4-20250514",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["llm_provider"] == "anthropic"
    assert data["llm_api_key_set"] is True
    assert data["llm_model"] == "claude-sonnet-4-20250514"

    # Verify key persists on re-read
    res2 = client.get("/api/settings", headers=auth_headers)
    assert res2.json()["llm_api_key_set"] is True


def test_put_settings_update_without_key(client, auth_headers):
    """Updating model/provider without sending key should keep existing key."""
    client.put("/api/settings", headers=auth_headers, json={
        "llm_provider": "openai",
        "llm_api_key": "sk-existing-key",
        "llm_model": "gpt-4o",
    })
    res = client.put("/api/settings", headers=auth_headers, json={
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
    })
    assert res.status_code == 200
    assert res.json()["llm_api_key_set"] is True


def test_put_settings_invalid_provider(client, auth_headers):
    res = client.put("/api/settings", headers=auth_headers, json={
        "llm_provider": "invalid-provider",
        "llm_model": "some-model",
    })
    assert res.status_code == 422


# ── Never returns plaintext key ──────────────────────────────────────────────

def test_settings_never_returns_key(client, auth_headers):
    client.put("/api/settings", headers=auth_headers, json={
        "llm_provider": "openai",
        "llm_api_key": "sk-secret-key-12345",
        "llm_model": "gpt-4o",
    })
    res = client.get("/api/settings", headers=auth_headers)
    body = res.text
    assert "sk-secret-key-12345" not in body
    assert "llm_api_key_set" in body


# ── Tenant isolation ─────────────────────────────────────────────────────────

def test_settings_tenant_isolation(client, auth_headers, second_auth_headers):
    # User A sets settings
    client.put("/api/settings", headers=auth_headers, json={
        "llm_provider": "anthropic",
        "llm_api_key": "sk-user-a",
        "llm_model": "claude-sonnet-4-20250514",
    })
    # User B should see defaults
    res = client.get("/api/settings", headers=second_auth_headers)
    assert res.json()["llm_api_key_set"] is False
    assert res.json()["llm_provider"] == "openai"
