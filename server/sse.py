"""In-memory SSE event bus for AgentLens real-time trace streaming."""

import asyncio
import json
from typing import AsyncGenerator


class SSEBus:
    """Broadcast events to all active SSE subscribers via per-subscriber queues."""

    def __init__(self):
        self._queues: list[asyncio.Queue] = []

    def publish(self, event_type: str, data: dict) -> None:
        """Push an event to all subscriber queues; drop dead queues on overflow."""
        payload = {"event": event_type, "data": data}
        dead = []
        for q in self._queues:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._queues.remove(q)

    async def subscribe(self) -> AsyncGenerator[str, None]:
        """Yield SSE-formatted strings for each published event."""
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._queues.append(q)
        try:
            while True:
                payload = await q.get()
                event = payload["event"]
                data = json.dumps(payload["data"])
                yield f"event: {event}\ndata: {data}\n\n"
        finally:
            if q in self._queues:
                self._queues.remove(q)


# Module-level singleton
bus = SSEBus()
