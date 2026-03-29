"""SQLModel table and Pydantic schemas for user LLM settings."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel
from sqlmodel import SQLModel, Field

VALID_PROVIDERS = {"openai", "anthropic", "gemini"}


class UserSettings(SQLModel, table=True):
    __tablename__ = "user_settings"
    id: str = Field(primary_key=True)
    user_id: str = Field(sa_column_kwargs={"unique": True}, index=True)
    llm_provider: str = Field(default="openai")
    llm_api_key_encrypted: Optional[str] = None
    llm_model: str = Field(default="gpt-4o-mini")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class SettingsIn(BaseModel):
    llm_provider: str = "openai"
    llm_api_key: Optional[str] = None  # plaintext — encrypted before storage
    llm_model: str = "gpt-4o-mini"


class SettingsOut(BaseModel):
    llm_provider: str
    llm_api_key_set: bool
    llm_model: str
