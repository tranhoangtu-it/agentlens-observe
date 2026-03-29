"""CRUD functions for autopsy results."""

import uuid
from typing import Optional

from sqlmodel import Session, select

from autopsy_models import AutopsyResult
from storage import _get_engine


def get_autopsy(trace_id: str, user_id: str) -> Optional[AutopsyResult]:
    """Get cached autopsy for a trace. Returns None if not found."""
    engine = _get_engine()
    with Session(engine) as session:
        stmt = select(AutopsyResult).where(
            AutopsyResult.trace_id == trace_id,
            AutopsyResult.user_id == user_id,
        )
        return session.exec(stmt).first()


def create_autopsy(data: dict) -> AutopsyResult:
    """Store an autopsy result."""
    engine = _get_engine()
    result = AutopsyResult(id=str(uuid.uuid4()), **data)
    with Session(engine) as session:
        session.add(result)
        session.commit()
        session.refresh(result)
    return result


def delete_autopsy(trace_id: str, user_id: str) -> bool:
    """Delete cached autopsy for re-run. Returns True if deleted."""
    engine = _get_engine()
    with Session(engine) as session:
        stmt = select(AutopsyResult).where(
            AutopsyResult.trace_id == trace_id,
            AutopsyResult.user_id == user_id,
        )
        result = session.exec(stmt).first()
        if not result:
            return False
        session.delete(result)
        session.commit()
    return True
