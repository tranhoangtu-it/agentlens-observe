"""CRUD functions for prompt templates and prompt versions."""

import difflib
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, col, select

from prompt_models import PromptTemplate, PromptVersion
from storage import _get_engine


def create_prompt(user_id: str, name: str) -> PromptTemplate:
    """Create a new prompt template for the given user."""
    engine = _get_engine()
    template = PromptTemplate(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=name,
    )
    with Session(engine) as session:
        session.add(template)
        session.commit()
        session.refresh(template)
    return template


def list_prompts(user_id: str) -> list[PromptTemplate]:
    """List all prompt templates owned by user, newest first."""
    engine = _get_engine()
    with Session(engine) as session:
        stmt = (
            select(PromptTemplate)
            .where(PromptTemplate.user_id == user_id)
            .order_by(col(PromptTemplate.created_at).desc())
        )
        return list(session.exec(stmt).all())


def get_prompt(prompt_id: str, user_id: str) -> Optional[PromptTemplate]:
    """Get a single prompt template. Returns None if not found or not owned."""
    engine = _get_engine()
    with Session(engine) as session:
        template = session.get(PromptTemplate, prompt_id)
        if not template or template.user_id != user_id:
            return None
        return template


def add_version(
    prompt_id: str,
    content: str,
    variables: Optional[list[str]],
    metadata: Optional[dict],
    user_id: str,
) -> Optional[PromptVersion]:
    """Append a new version to a prompt template. Auto-increments version number.

    Returns None if prompt not found or not owned by user.
    """
    engine = _get_engine()
    with Session(engine) as session:
        template = session.get(PromptTemplate, prompt_id)
        if not template or template.user_id != user_id:
            return None

        # Use DB-level MAX to avoid race conditions on concurrent version creation
        from sqlalchemy import func as sa_func
        max_stmt = select(sa_func.coalesce(sa_func.max(PromptVersion.version), 0)).where(
            PromptVersion.prompt_id == prompt_id
        )
        current_max = session.exec(max_stmt).one()
        next_version = current_max + 1

        pv = PromptVersion(
            id=str(uuid.uuid4()),
            prompt_id=prompt_id,
            user_id=user_id,
            version=next_version,
            content=content,
            variables_json=json.dumps(variables or []),
            metadata_json=json.dumps(metadata or {}),
        )
        template.latest_version = next_version
        template.updated_at = datetime.now(timezone.utc)

        session.add(pv)
        session.add(template)
        try:
            session.commit()
        except Exception:
            session.rollback()
            return None
        session.refresh(pv)
    return pv


def get_version(prompt_id: str, version: int, user_id: str) -> Optional[PromptVersion]:
    """Get a specific version of a prompt. Returns None if not found or not owned."""
    engine = _get_engine()
    with Session(engine) as session:
        stmt = (
            select(PromptVersion)
            .where(PromptVersion.prompt_id == prompt_id)
            .where(PromptVersion.version == version)
            .where(PromptVersion.user_id == user_id)
        )
        return session.exec(stmt).first()


def list_versions(prompt_id: str, user_id: str) -> list[PromptVersion]:
    """List all versions for a prompt template, oldest first."""
    engine = _get_engine()
    with Session(engine) as session:
        stmt = (
            select(PromptVersion)
            .where(PromptVersion.prompt_id == prompt_id)
            .where(PromptVersion.user_id == user_id)
            .order_by(col(PromptVersion.version).asc())
        )
        return list(session.exec(stmt).all())


def diff_versions(
    prompt_id: str, v1: int, v2: int, user_id: str
) -> Optional[dict]:
    """Produce a unified diff between two versions of a prompt.

    Returns dict with keys: v1, v2, diff (unified diff string).
    Returns None if either version is not found.
    """
    ver1 = get_version(prompt_id, v1, user_id)
    ver2 = get_version(prompt_id, v2, user_id)
    if not ver1 or not ver2:
        return None

    lines1 = ver1.content.splitlines(keepends=True)
    lines2 = ver2.content.splitlines(keepends=True)
    diff_lines = list(
        difflib.unified_diff(
            lines1,
            lines2,
            fromfile=f"v{v1}",
            tofile=f"v{v2}",
        )
    )
    return {"v1": v1, "v2": v2, "diff": "".join(diff_lines)}
