"""Auto-discover and load server plugins from the plugins/ directory."""

import importlib
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI

from plugin_protocol import ServerPlugin

logger = logging.getLogger(__name__)

_plugins: list[ServerPlugin] = []

_PLUGINS_DIR = Path(__file__).parent / "plugins"


def load_plugins(app: FastAPI) -> list[ServerPlugin]:
    """Discover and load all plugins from server/plugins/ directory.

    Each .py file in plugins/ must expose a module-level `plugin` attribute
    that implements the ServerPlugin protocol.
    """
    global _plugins
    _plugins = []

    if not _PLUGINS_DIR.is_dir():
        logger.debug("No plugins directory found at %s", _PLUGINS_DIR)
        return _plugins

    for filepath in sorted(_PLUGINS_DIR.glob("*.py")):
        if filepath.name.startswith("_"):
            continue
        module_name = f"plugins.{filepath.stem}"
        try:
            mod = importlib.import_module(module_name)
            plugin = getattr(mod, "plugin", None)
            if plugin is None:
                logger.warning("Plugin %s has no 'plugin' attribute, skipping", module_name)
                continue
            # Validate plugin implements required protocol methods
            if not isinstance(plugin, ServerPlugin):
                logger.warning("Plugin %s does not implement ServerPlugin protocol, skipping", module_name)
                continue
            plugin.register_routes(app)
            _plugins.append(plugin)
            logger.info("Loaded plugin: %s", plugin.name)
        except Exception as exc:
            logger.error("Failed to load plugin %s: %s", module_name, exc)

    return _plugins


def notify_trace_created(trace_id: str, agent_name: str, span_count: int) -> None:
    """Notify all plugins that a trace was created."""
    for plugin in _plugins:
        try:
            plugin.on_trace_created(trace_id, agent_name, span_count)
        except Exception as exc:
            logger.error("Plugin %s on_trace_created error: %s", plugin.name, exc)


def notify_trace_completed(trace_id: str, agent_name: str) -> None:
    """Notify all plugins that a trace completed."""
    for plugin in _plugins:
        try:
            plugin.on_trace_completed(trace_id, agent_name)
        except Exception as exc:
            logger.error("Plugin %s on_trace_completed error: %s", plugin.name, exc)
