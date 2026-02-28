"""Fixtures for SDK tests."""

import sys
from pathlib import Path

import pytest
import httpx
import respx

# Add SDK to path
sdk_root = Path(__file__).parent.parent
sys.path.insert(0, str(sdk_root))


@pytest.fixture(autouse=True)
def mock_http():
    """Mock all HTTP calls using respx."""
    with respx.mock:
        # Mock trace ingestion endpoint
        respx.post("http://localhost:3000/api/traces").mock(return_value=httpx.Response(201))

        # Mock span ingestion endpoint
        respx.post("http://localhost:3000/api/traces/__id__/spans", path__regex=True).mock(
            return_value=httpx.Response(201)
        )

        # Mock batch endpoint
        respx.post("http://localhost:3000/api/traces/batch").mock(return_value=httpx.Response(201))

        yield
