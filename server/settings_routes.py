"""API routes for user LLM settings."""

from fastapi import APIRouter, Depends, HTTPException

from auth_deps import get_current_user
from auth_models import User
from settings_models import SettingsIn, SettingsOut, VALID_PROVIDERS
from settings_storage import get_settings, upsert_settings

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings")
def get_settings_endpoint(user: User = Depends(get_current_user)) -> SettingsOut:
    """Get current LLM settings. Never returns the actual API key."""
    settings = get_settings(user.id)
    if not settings:
        return SettingsOut(
            llm_provider="openai",
            llm_api_key_set=False,
            llm_model="gpt-4o-mini",
        )
    return SettingsOut(
        llm_provider=settings.llm_provider,
        llm_api_key_set=bool(settings.llm_api_key_encrypted),
        llm_model=settings.llm_model,
    )


@router.put("/settings")
def update_settings_endpoint(
    body: SettingsIn,
    user: User = Depends(get_current_user),
) -> SettingsOut:
    """Update LLM settings. API key is encrypted before storage."""
    if body.llm_provider not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid provider: {body.llm_provider}. Must be one of: {', '.join(sorted(VALID_PROVIDERS))}",
        )

    data = body.model_dump()
    settings = upsert_settings(user.id, data)
    return SettingsOut(
        llm_provider=settings.llm_provider,
        llm_api_key_set=bool(settings.llm_api_key_encrypted),
        llm_model=settings.llm_model,
    )
