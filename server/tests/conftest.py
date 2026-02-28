"""Fixtures for server tests: test DB, API client."""

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


@pytest.fixture(autouse=True)
def test_db(tmp_path):
    """Use fresh in-memory SQLite for each test."""
    # Create test DB file in temp directory
    db_path = tmp_path / "test.db"

    # Create engine with test database
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # Create tables
    SQLModel.metadata.create_all(engine)

    # Enable WAL mode like production
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.commit()

    # Replace global engine
    storage._engine = engine

    yield engine

    # Cleanup
    storage._engine = None


@pytest.fixture
def client(test_db):
    """FastAPI test client."""
    return TestClient(app)


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
