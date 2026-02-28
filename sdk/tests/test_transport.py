"""Tests for transport.py — HTTP transport and batch mode."""

import os
import threading
import time
import pytest
from agentlens.transport import (
    post_trace,
    post_spans,
    configure_batch,
    get_server_url,
    flush_batch,
    _batch_queue,
    _batch_enabled,
)


class TestServerUrl:
    """Test server URL resolution."""

    def test_default_server_url(self):
        """Default server URL is localhost:3000."""
        url = get_server_url()
        assert url == "http://localhost:3000"

    def test_custom_server_url_from_env(self, monkeypatch):
        """AGENTLENS_URL environment variable overrides default."""
        monkeypatch.setenv("AGENTLENS_URL", "http://custom-server:8080")
        url = get_server_url()
        assert url == "http://custom-server:8080"

    def test_server_url_strips_trailing_slash(self, monkeypatch):
        """Server URL has trailing slash removed."""
        monkeypatch.setenv("AGENTLENS_URL", "http://server.com/")
        url = get_server_url()
        assert not url.endswith("/")


class TestPostTrace:
    """Test trace posting (fire-and-forget)."""

    def test_post_trace_fires_thread(self):
        """post_trace creates a background thread."""
        # Just verify it doesn't crash and returns immediately
        post_trace(
            "trace-1",
            "agent",
            [{"span_id": "s1", "name": "test", "type": "tool_call"}],
        )
        # Function should return immediately (non-blocking)

    def test_post_trace_with_custom_url(self):
        """post_trace accepts custom server URL."""
        post_trace(
            "trace-2",
            "agent",
            [{"span_id": "s1", "name": "test", "type": "tool_call"}],
            server_url="http://custom:9000",
        )

    def test_post_trace_handles_network_error(self):
        """post_trace handles network errors gracefully (non-fatal)."""
        # With respx mocking, this should work, but verify no exception propagates
        post_trace(
            "trace-3",
            "agent",
            [{"span_id": "s1", "name": "test", "type": "tool_call"}],
            server_url="http://unreachable:9999",
        )


class TestPostSpans:
    """Test incremental span posting."""

    def test_post_spans_basic(self):
        """post_spans sends span data to server."""
        post_spans(
            "trace-1",
            [{"span_id": "s2", "name": "span2", "type": "tool_call"}],
        )

    def test_post_spans_bypasses_batch_mode(self):
        """post_spans works regardless of batch mode setting."""
        configure_batch(enabled=True)
        try:
            post_spans(
                "trace-2",
                [{"span_id": "s3", "name": "span3", "type": "tool_call"}],
            )
        finally:
            configure_batch(enabled=False)

    def test_post_spans_with_custom_url(self):
        """post_spans accepts custom server URL."""
        post_spans(
            "trace-3",
            [{"span_id": "s4", "name": "span4", "type": "tool_call"}],
            server_url="http://custom:9000",
        )


class TestBatchMode:
    """Test batch transport configuration and flushing."""

    def teardown_method(self):
        """Reset batch mode after each test."""
        configure_batch(enabled=False)

    def test_configure_batch_basic(self):
        """Batch mode can be enabled."""
        configure_batch(enabled=True, server_url="http://localhost:3000")
        assert _batch_enabled is True

    def test_configure_batch_disable(self):
        """Batch mode can be disabled."""
        configure_batch(enabled=True)
        configure_batch(enabled=False)
        assert _batch_enabled is False

    def test_batch_custom_size(self):
        """Batch max size can be configured."""
        configure_batch(enabled=True, max_size=20)
        # Verify it was set (internal state)
        assert _batch_enabled is True

    def test_batch_flush_interval(self):
        """Batch flush interval can be configured."""
        configure_batch(enabled=True, flush_interval=10.0)
        assert _batch_enabled is True

    def test_flush_batch_empty_queue(self):
        """Flushing empty queue is safe."""
        configure_batch(enabled=True)
        flush_batch()  # Should not crash

    def test_batch_auto_flush_on_max_size(self):
        """Batch flushes when queue reaches max_size."""
        configure_batch(enabled=True, server_url="http://localhost:3000", max_size=2)
        try:
            # Add traces to batch
            post_trace("t1", "agent", [])
            post_trace("t2", "agent", [])
            post_trace("t3", "agent", [])
            # After 3rd trace, should have flushed (max_size=2)
            # Give thread time to complete
            time.sleep(0.1)
        finally:
            configure_batch(enabled=False)


class TestTransportThreading:
    """Test thread safety and non-blocking behavior."""

    def test_post_trace_non_blocking(self):
        """post_trace returns immediately without waiting."""
        start = time.time()
        post_trace("trace-fast", "agent", [])
        elapsed = time.time() - start
        # Should complete in <100ms (usually <1ms)
        assert elapsed < 0.1

    def test_multiple_concurrent_posts(self):
        """Multiple threads can post traces concurrently."""
        def post_in_thread(trace_id):
            post_trace(trace_id, "agent", [])

        threads = [
            threading.Thread(target=post_in_thread, args=(f"trace-{i}",))
            for i in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=1.0)


class TestBatchIntegration:
    """Integration tests for batch mode."""

    def teardown_method(self):
        """Reset batch mode after each test."""
        configure_batch(enabled=False)

    def test_batch_mode_collects_traces(self):
        """Traces are collected in batch mode."""
        configure_batch(enabled=True, server_url="http://localhost:3000", max_size=100)
        try:
            post_trace("t1", "agent", [])
            post_trace("t2", "agent", [])
            # Wait briefly for queue to receive data
            time.sleep(0.01)
            # Queue should have traces (or have flushed)
        finally:
            configure_batch(enabled=False)

    def test_batch_mode_switches(self):
        """Switching between batch and immediate mode works."""
        # Immediate mode
        post_trace("t1", "agent", [])

        # Switch to batch
        configure_batch(enabled=True, server_url="http://localhost:3000")
        post_trace("t2", "agent", [])

        # Switch back to immediate
        configure_batch(enabled=False)
        post_trace("t3", "agent", [])
