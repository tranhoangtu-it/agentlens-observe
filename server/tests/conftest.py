"""Fixtures for server tests: test DB, API client, auth helpers."""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlmodel import SQLModel, create_engine, Session

# Import after path manipulation to ensure tests can find modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
import storage
from models import Trace, Span
from auth_models import User, ApiKey  # noqa: F401 — register auth tables
from settings_models import UserSettings  # noqa: F401 — register settings table
from autopsy_models import AutopsyResult  # noqa: F401 — register autopsy table


@pytest.fixture(autouse=True)
def test_db(tmp_path):
    """Fresh DB for each test. Uses TEST_DATABASE_URL (Postgres) or SQLite."""
    test_url = os.environ.get("TEST_DATABASE_URL")

    if test_url:
        # PostgreSQL: create tables, run test, then drop tables
        engine = create_engine(test_url, echo=False)
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)
    else:
        # SQLite: temp file per test
        db_path = tmp_path / "test.db"
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )
        SQLModel.metadata.create_all(engine)
        with engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.commit()

    # Replace global engine
    storage._engine = engine

    yield engine

    # Cleanup
    if test_url:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()
    storage._engine = None


@pytest.fixture
def client(test_db):
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Register a test user and return auth headers dict."""
    res = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "testpass123",
        "display_name": "Test User",
    })
    assert res.status_code == 201
    data = res.json()
    return {"Authorization": f"Bearer {data['token']}"}


@pytest.fixture
def second_auth_headers(client):
    """Register a second user for cross-tenant tests."""
    res = client.post("/api/auth/register", json={
        "email": "other@example.com",
        "password": "otherpass123",
        "display_name": "Other User",
    })
    assert res.status_code == 201
    data = res.json()
    return {"Authorization": f"Bearer {data['token']}"}


@pytest.fixture
def sample_trace_data():
    """Sample trace with spans for testing. Use unique IDs per test."""
    import uuid
    base_id = str(uuid.uuid4())
    return {
        "trace_id": f"test-trace-{base_id}",
        "agent_name": "search_agent",
        "spans": [
            {
                "span_id": f"span-1-{base_id}",
                "parent_id": None,
                "name": "search_agent",
                "type": "agent_run",
                "start_ms": 1000,
                "end_ms": 5000,
                "input": "find python tutorials",
                "output": "tutorial_links",
                "cost": {
                    "model": "gpt-4o",
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "usd": 0.001,
                },
                "metadata": {"version": "1.0"},
            },
            {
                "span_id": f"span-2-{base_id}",
                "parent_id": f"span-1-{base_id}",
                "name": "search",
                "type": "tool_call",
                "start_ms": 1100,
                "end_ms": 3000,
                "input": "python tutorials",
                "output": "[url1, url2, url3]",
                "cost": None,
                "metadata": {},
            },
        ],
    }


@pytest.fixture
def sample_spans_data(sample_trace_data):
    """Sample spans for incremental ingestion. Uses IDs from sample_trace_data."""
    # Extract base ID from first span
    first_span_id = sample_trace_data["spans"][0]["span_id"]
    base_id = first_span_id.split("-", 2)[2]  # Extract UUID from "span-1-{uuid}"

    return {
        "spans": [
            {
                "span_id": f"span-3-{base_id}",
                "parent_id": f"span-1-{base_id}",
                "name": "filter",
                "type": "tool_call",
                "start_ms": 3100,
                "end_ms": 4500,
                "input": "tutorial_links",
                "output": "top_3_links",
                "cost": None,
                "metadata": {},
            },
        ]
    }
