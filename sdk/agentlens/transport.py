"""Non-blocking HTTP transport. Posts traces/spans to AgentLens server in background thread.

Supports three modes:
- Immediate: each post_trace / post_spans call fires a background thread instantly (default)
- Batch: spans are queued and flushed every N seconds or when queue reaches N items
"""
import logging
import os
import threading
from typing import Optional

import httpx

logger = logging.getLogger("agentlens.transport")

_TIMEOUT = httpx.Timeout(5.0)
_api_key: Optional[str] = None


def set_api_key(key: str) -> None:
    """Set the API key for authenticated transport."""
    global _api_key
    _api_key = key


def _auth_headers() -> dict:
    """Build auth headers if API key is configured."""
    if _api_key:
        return {"X-API-Key": _api_key}
    return {}


# --- Batch transport state (module-level, opt-in) ---
_batch_lock = threading.Lock()
_batch_queue: list[dict] = []          # list of trace payloads
_batch_timer: Optional[threading.Timer] = None
_batch_max_size: int = 10              # flush when queue reaches this many items
_batch_flush_interval: float = 5.0    # flush every N seconds
_batch_enabled: bool = False
_batch_server_url: Optional[str] = None


def get_server_url() -> str:
    return os.getenv("AGENTLENS_URL", "http://localhost:3000").rstrip("/")


def configure_batch(
    enabled: bool = True,
    server_url: Optional[str] = None,
    max_size: int = 10,
    flush_interval: float = 5.0,
) -> None:
    """Enable batch transport mode.

    Args:
        enabled: Toggle batch mode. When False, reverts to immediate mode.
        server_url: Override server URL for batch flush endpoint.
        max_size: Flush when queue reaches this many traces.
        flush_interval: Auto-flush every N seconds (restarted after each flush).
    """
    global _batch_enabled, _batch_server_url, _batch_max_size, _batch_flush_interval
    with _batch_lock:
        _batch_enabled = enabled
        _batch_server_url = server_url
        _batch_max_size = max_size
        _batch_flush_interval = flush_interval
    if enabled:
        _schedule_batch_flush()
    else:
        _cancel_batch_timer()


def _cancel_batch_timer() -> None:
    global _batch_timer
    with _batch_lock:
        if _batch_timer is not None:
            _batch_timer.cancel()
            _batch_timer = None


def _schedule_batch_flush() -> None:
    """Schedule a timer to auto-flush the batch queue."""
    global _batch_timer
    _cancel_batch_timer()
    with _batch_lock:
        if not _batch_enabled:
            return
        interval = _batch_flush_interval
    t = threading.Timer(interval, flush_batch)
    t.daemon = True
    with _batch_lock:
        _batch_timer = t
    t.start()


def flush_batch() -> None:
    """Flush all queued trace payloads to server in a single background thread.

    Called automatically by the timer or when queue reaches max_size.
    Safe to call manually at program exit.
    """
    with _batch_lock:
        if not _batch_queue:
            # Re-schedule even when nothing to send (keeps timer alive)
            if _batch_enabled:
                _schedule_batch_flush()
            return
        payloads = list(_batch_queue)
        _batch_queue.clear()
        url = (_batch_server_url or get_server_url()) + "/api/traces/batch"

    def _send():
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.post(url, json={"traces": payloads})
                if resp.status_code not in (200, 201):
                    logger.debug("AgentLens batch transport returned %s", resp.status_code)
        except Exception as exc:
            logger.debug("AgentLens batch transport error (non-fatal): %s", exc)
        finally:
            # Re-schedule next flush
            with _batch_lock:
                if _batch_enabled:
                    _schedule_batch_flush()

    t = threading.Thread(target=_send, daemon=True)
    t.start()


def post_trace(
    trace_id: str,
    agent_name: str,
    spans: list[dict],
    server_url: Optional[str] = None,
) -> None:
    """Fire-and-forget: POST full trace to /api/traces.

    When batch mode is enabled, queues the trace and flushes when the queue
    hits max_size or the flush timer fires.  Falls back to immediate mode
    when batch is disabled (default).
    """
    payload = {"trace_id": trace_id, "agent_name": agent_name, "spans": spans}

    with _batch_lock:
        batch_on = _batch_enabled

    if batch_on:
        with _batch_lock:
            _batch_queue.append(payload)
            should_flush = len(_batch_queue) >= _batch_max_size
        if should_flush:
            flush_batch()
        return

    # Immediate mode — existing behaviour
    url = (server_url or get_server_url()) + "/api/traces"

    def _send():
        try:
            headers = {"Content-Type": "application/json", **_auth_headers()}
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.post(url, json=payload, headers=headers)
                if resp.status_code not in (200, 201):
                    logger.debug("AgentLens server returned %s", resp.status_code)
        except Exception as exc:
            logger.debug("AgentLens transport error (non-fatal): %s", exc)

    t = threading.Thread(target=_send, daemon=True)
    t.start()


def post_spans(
    trace_id: str,
    spans: list[dict],
    server_url: Optional[str] = None,
) -> None:
    """Fire-and-forget incremental: POST spans to /api/traces/{trace_id}/spans.

    Used by streaming mode — sends spans as they complete without waiting for the
    full trace to finish. Safe to call from any thread; never blocks the caller.
    Bypasses batch mode intentionally (streaming requires immediate delivery).
    """
    url = (server_url or get_server_url()) + f"/api/traces/{trace_id}/spans"
    payload = {"spans": spans}

    def _send():
        try:
            headers = {"Content-Type": "application/json", **_auth_headers()}
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.post(url, json=payload, headers=headers)
                if resp.status_code not in (200, 201):
                    logger.debug(
                        "AgentLens incremental transport returned %s for trace %s",
                        resp.status_code,
                        trace_id,
                    )
        except Exception as exc:
            logger.debug("AgentLens incremental transport error (non-fatal): %s", exc)

    t = threading.Thread(target=_send, daemon=True)
    t.start()
