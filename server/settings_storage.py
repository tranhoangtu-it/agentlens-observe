"""CRUD functions for user LLM settings."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from crypto import encrypt_value, decrypt_value
from settings_models import UserSettings
from storage import _get_engine


def get_settings(user_id: str) -> Optional[UserSettings]:
    """Get settings for a user. Returns None if not configured."""
    engine = _get_engine()
    with Session(engine) as session:
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        return session.exec(stmt).first()


def upsert_settings(user_id: str, data: dict) -> UserSettings:
    """Create or update user settings. Encrypts llm_api_key if provided."""
    engine = _get_engine()
    with Session(engine) as session:
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        existing = session.exec(stmt).first()

        # Encrypt API key if provided
        api_key_plain = data.pop("llm_api_key", None)

        if existing:
            for key, val in data.items():
                if val is not None:
                    setattr(existing, key, val)
            if api_key_plain:
                existing.llm_api_key_encrypted = encrypt_value(api_key_plain)
            existing.updated_at = datetime.now(timezone.utc)
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing

        settings = UserSettings(
            id=str(uuid.uuid4()),
            user_id=user_id,
            **data,
        )
        if api_key_plain:
            settings.llm_api_key_encrypted = encrypt_value(api_key_plain)
        session.add(settings)
        session.commit()
        session.refresh(settings)
        return settings


def get_decrypted_api_key(user_id: str) -> Optional[str]:
    """Get the decrypted LLM API key for a user. Returns None if not set."""
    settings = get_settings(user_id)
    if not settings or not settings.llm_api_key_encrypted:
        return None
    return decrypt_value(settings.llm_api_key_encrypted)
