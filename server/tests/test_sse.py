"""Tests for SSE bus in sse.py."""

import asyncio
import pytest
from sse import bus


@pytest.mark.asyncio
async def test_publish_subscribe_basic():
    """Publish event, subscriber receives it."""
    events = []

    async def subscriber():
        async for event in bus.subscribe():
            events.append(event)
            if len(events) >= 1:
                break

    # Start subscriber task
    sub_task = asyncio.create_task(subscriber())

    # Give subscriber time to set up
    await asyncio.sleep(0.01)

    # Publish event
    bus.publish("test_event", {"data": "test"})

    # Wait for subscriber to receive
    await asyncio.wait_for(sub_task, timeout=1.0)

    assert len(events) == 1
    assert "test_event" in events[0]
    assert "test" in events[0]


@pytest.mark.asyncio
async def test_multiple_subscribers():
    """All subscribers receive same event."""
    events1 = []
    events2 = []

    async def subscriber1():
        async for event in bus.subscribe():
            events1.append(event)
            if len(events1) >= 1:
                break

    async def subscriber2():
        async for event in bus.subscribe():
            events2.append(event)
            if len(events2) >= 1:
                break

    # Start both subscribers
    task1 = asyncio.create_task(subscriber1())
    task2 = asyncio.create_task(subscriber2())

    # Give subscribers time to set up
    await asyncio.sleep(0.01)

    # Publish event
    bus.publish("shared_event", {"shared": "data"})

    # Wait for both subscribers
    await asyncio.wait_for(asyncio.gather(task1, task2), timeout=1.0)

    assert len(events1) == 1
    assert len(events2) == 1
    assert "shared" in events1[0]
    assert "shared" in events2[0]


@pytest.mark.asyncio
async def test_event_format():
    """Published events are properly formatted for SSE."""
    events = []

    async def subscriber():
        async for event in bus.subscribe():
            events.append(event)
            if len(events) >= 1:
                break

    sub_task = asyncio.create_task(subscriber())
    await asyncio.sleep(0.01)

    # Publish with event type and data
    bus.publish("trace_created", {"trace_id": "123", "agent_name": "test_agent"})

    await asyncio.wait_for(sub_task, timeout=1.0)

    # Verify SSE format (event: ...\ndata: ...\n\n)
    event_str = events[0]
    assert "event:" in event_str
    assert "data:" in event_str
    assert "trace_created" in event_str or "123" in event_str
