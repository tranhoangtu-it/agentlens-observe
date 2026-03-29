"""Symmetric encryption helpers for storing sensitive values (API keys)."""

import base64
import hashlib
import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_jwt_secret = os.environ.get("AGENTLENS_JWT_SECRET", "")

if not _jwt_secret:
    logger.warning(
        "AGENTLENS_JWT_SECRET is not set — encrypted values will be lost on restart. "
        "Set AGENTLENS_JWT_SECRET in production to persist stored API keys."
    )


def _get_fernet() -> Fernet:
    """Derive a Fernet key from the JWT secret."""
    secret = _jwt_secret or "agentlens-dev-fallback-key"
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value. Returns base64-encoded ciphertext."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str | None:
    """Decrypt a ciphertext. Returns None if decryption fails."""
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception):
        logger.warning("Failed to decrypt value — key may have changed.")
        return None
