"""Tests for server-side plugin loading and notification."""

import importlib
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from fastapi import FastAPI

from plugin_loader import load_plugins, notify_trace_created, notify_trace_completed, _plugins


@pytest.fixture(autouse=True)
def clean_plugins():
    """Ensure clean plugin state for each test."""
    _plugins.clear()
    yield
    _plugins.clear()


class FakePlugin:
    name = "test-plugin"

    def __init__(self):
        self.created_calls = []
        self.completed_calls = []

    def on_trace_created(self, trace_id, agent_name, span_count):
        self.created_calls.append((trace_id, agent_name, span_count))

    def on_trace_completed(self, trace_id, agent_name):
        self.completed_calls.append((trace_id, agent_name))

    def register_routes(self, app):
        pass


def test_notify_trace_created():
    """Plugin receives on_trace_created calls."""
    plugin = FakePlugin()
    _plugins.append(plugin)

    notify_trace_created("t1", "agent-x", 3)
    assert plugin.created_calls == [("t1", "agent-x", 3)]


def test_notify_trace_completed():
    """Plugin receives on_trace_completed calls."""
    plugin = FakePlugin()
    _plugins.append(plugin)

    notify_trace_completed("t2", "agent-y")
    assert plugin.completed_calls == [("t2", "agent-y")]


def test_plugin_error_does_not_propagate():
    """Plugin errors are caught, don't crash the server."""

    class BadPlugin:
        name = "bad-plugin"
        def on_trace_created(self, *a): raise RuntimeError("boom")
        def on_trace_completed(self, *a): raise RuntimeError("boom")
        def register_routes(self, app): pass

    _plugins.append(BadPlugin())
    # Should not raise
    notify_trace_created("t3", "agent-z", 1)
    notify_trace_completed("t3", "agent-z")


def test_load_plugins_empty_dir(tmp_path):
    """load_plugins with empty plugins dir returns empty list."""
    app = FastAPI()
    with patch("plugin_loader._PLUGINS_DIR", tmp_path):
        result = load_plugins(app)
    assert result == []


def test_load_plugins_with_plugin(tmp_path):
    """load_plugins discovers and loads plugin from .py file."""
    # Create a plugin file
    plugin_code = '''
class _Plugin:
    name = "sample-plugin"
    def on_trace_created(self, trace_id, agent_name, span_count): pass
    def on_trace_completed(self, trace_id, agent_name): pass
    def register_routes(self, app): pass

plugin = _Plugin()
'''
    (tmp_path / "sample.py").write_text(plugin_code)

    app = FastAPI()
    mock_mod = type("Module", (), {})()
    # Use FakePlugin (real protocol impl) instead of MagicMock for isinstance check
    fake = FakePlugin()
    mock_mod.plugin = fake

    with patch("plugin_loader._PLUGINS_DIR", tmp_path), \
         patch("plugin_loader.importlib.import_module", return_value=mock_mod):
        result = load_plugins(app)

    assert len(result) == 1
    assert result[0].name == "test-plugin"
