"""Non-blocking HTTP transport. Posts traces to AgentLens server in background thread."""
import logging
import os
import threading
from typing import Optional

import httpx

logger = logging.getLogger("agentlens.transport")

_TIMEOUT = httpx.Timeout(5.0)


def get_server_url() -> str:
    return os.getenv("AGENTLENS_URL", "http://localhost:3000").rstrip("/")


def post_trace(
    trace_id: str,
    agent_name: str,
    spans: list[dict],
    server_url: Optional[str] = None,
) -> None:
    """Fire-and-forget: spawn daemon thread, never blocks caller."""
    url = (server_url or get_server_url()) + "/api/traces"
    payload = {"trace_id": trace_id, "agent_name": agent_name, "spans": spans}

    def _send():
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.post(url, json=payload)
                if resp.status_code not in (200, 201):
                    logger.debug("AgentLens server returned %s", resp.status_code)
        except Exception as exc:
            logger.debug("AgentLens transport error (non-fatal): %s", exc)

    t = threading.Thread(target=_send, daemon=True)
    t.start()
