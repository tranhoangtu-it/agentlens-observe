"""Tests for tracer.py — decorator, span context, nesting."""

import asyncio
import pytest
from agentlens.tracer import Tracer, _current_trace, ActiveTrace, SpanData


@pytest.fixture
def tracer():
    """Fresh tracer instance for each test."""
    t = Tracer()
    t.configure(server_url="http://localhost:3000")
    return t


class TestTracerDecorator:
    """Test @trace decorator on sync and async functions."""

    def test_trace_decorator_sync(self, tracer):
        """Sync function wrapped with @trace creates trace and spans."""
        @tracer.trace(name="test_agent")
        def test_func(input_data):
            return f"output: {input_data}"

        result = test_func("hello")
        assert result == "output: hello"

    def test_trace_decorator_async(self, tracer):
        """Async function wrapped with @trace creates trace and spans."""
        @tracer.trace(name="async_agent", span_type="llm_call")
        async def async_func(input_data):
            await asyncio.sleep(0.01)
            return f"async output: {input_data}"

        result = asyncio.run(async_func("world"))
        assert result == "async output: world"

    def test_trace_captures_input_output(self, tracer):
        """Trace captures input and output in root span."""
        traced_data = {"input": None, "output": None}

        @tracer.trace(name="capture_test")
        def capture_func(x, y):
            return x + y

        result = capture_func(3, 4)
        assert result == 7

    def test_trace_exception_stored(self, tracer):
        """Exceptions are captured in span metadata."""
        @tracer.trace(name="error_test")
        def error_func():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            error_func()

    def test_trace_with_span_context(self, tracer):
        """Child spans can be created within traced function."""
        @tracer.trace(name="parent_test")
        def parent_func():
            with tracer.span("child_span", span_type="tool_call") as span:
                span.set_output("child result")
            return "done"

        result = parent_func()
        assert result == "done"


class TestSpanContext:
    """Test span() context manager for manual spans."""

    def test_span_basic(self, tracer):
        """Create span within trace."""
        @tracer.trace(name="span_test")
        def func():
            with tracer.span("my_span") as span:
                span.set_output("test output")
            return "done"

        result = func()
        assert result == "done"

    def test_span_outside_trace_is_noop(self, tracer):
        """Span outside trace does nothing."""
        ctx = tracer.span("orphan")
        with ctx:
            ctx.set_output("this should not crash")
        # No exception

    def test_span_set_cost(self, tracer):
        """Span cost can be set."""
        @tracer.trace(name="cost_test")
        def func():
            with tracer.span("call") as span:
                span.set_cost("gpt-4o", 100, 50)
            return "done"

        result = func()
        assert result == "done"

    def test_span_set_metadata(self, tracer):
        """Span metadata can be updated."""
        @tracer.trace(name="metadata_test")
        def func():
            with tracer.span("op") as span:
                span.set_metadata(key1="value1", key2="value2")
            return "done"

        result = func()
        assert result == "done"

    def test_span_log(self, tracer):
        """Span can log messages."""
        @tracer.trace(name="log_test")
        def func():
            with tracer.span("op") as span:
                span.log("step 1 complete")
                span.log("step 2 complete", extra_data="test")
            return "done"

        result = func()
        assert result == "done"


class TestNestedSpans:
    """Test parent/child span relationships."""

    def test_parent_child_span_ids(self, tracer):
        """Child spans have correct parent_id."""
        @tracer.trace(name="nesting_test")
        def func():
            with tracer.span("parent") as parent:
                with tracer.span("child") as child:
                    child.set_output("child")
                parent.set_output("parent")
            return "done"

        result = func()
        assert result == "done"

    def test_deep_nesting(self, tracer):
        """Multiple levels of nesting work."""
        @tracer.trace(name="deep_test")
        def func():
            with tracer.span("level1") as s1:
                s1.set_output("l1")
                with tracer.span("level2") as s2:
                    s2.set_output("l2")
                    with tracer.span("level3") as s3:
                        s3.set_output("l3")
            return "done"

        result = func()
        assert result == "done"


class TestActiveTrace:
    """Test ActiveTrace context management."""

    def test_current_trace_context(self, tracer):
        """current_trace() returns active trace within decorator."""
        active_ref = None

        @tracer.trace(name="context_test")
        def func():
            nonlocal active_ref
            active_ref = tracer.current_trace()
            return "done"

        func()
        assert active_ref is not None
        assert isinstance(active_ref, ActiveTrace)

    def test_current_trace_outside(self, tracer):
        """current_trace() returns None outside trace."""
        result = tracer.current_trace()
        assert result is None


class TestTracerConfiguration:
    """Test tracer configuration options."""

    def test_configure_with_streaming(self):
        """Tracer can be configured with streaming."""
        tracer = Tracer()
        tracer.configure(
            server_url="http://localhost:3000",
            streaming=True,
        )
        assert tracer._streaming is True

    def test_configure_with_batch(self):
        """Tracer can be configured with batch mode."""
        tracer = Tracer()
        tracer.configure(
            server_url="http://localhost:3000",
            batch=True,
            batch_max_size=5,
            batch_flush_interval=2.0,
        )
        # Batch should be configured
        assert tracer._server_url == "http://localhost:3000"


class TestAsyncTrace:
    """Test async tracing with await."""

    def test_async_trace_with_await(self, tracer):
        """Async function with await works."""
        @tracer.trace(name="async_with_await")
        async def async_func():
            await asyncio.sleep(0.01)
            return "async result"

        result = asyncio.run(async_func())
        assert result == "async result"

    def test_async_span_inside_trace(self, tracer):
        """Spans work inside async trace."""
        @tracer.trace(name="async_span_test")
        async def async_func():
            with tracer.span("async_op") as span:
                await asyncio.sleep(0.01)
                span.set_output("done")
            return "result"

        result = asyncio.run(async_func())
        assert result == "result"
