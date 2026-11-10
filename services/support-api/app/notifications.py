"""SSE notification manager for real-time event broadcasting.

Uses an asyncio-based pub/sub pattern:
- Each connected SSE client gets its own asyncio.Queue.
- The manager tracks all active queues and broadcasts events to every subscriber.
- Events carry an auto-incrementing `event_id` for Last-Event-ID recovery.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


# ── Event types ──────────────────────────────────────────────────────

# Event names that the system can emit.
EVENT_RFP_TICKET_CREATED = "rfp_ticket_created"

# Optional event names (Part 2 / bonus)
EVENT_KPI_THRESHOLD_ALERT = "kpi_threshold_alert"
EVENT_SUPPORT_TICKET_ESCALATED = "support_ticket_escalated"


# ── Data structures ──────────────────────────────────────────────────


@dataclass
class SSEEvent:
    """A single SSE event to be serialized onto the wire."""

    event: str
    data: dict
    event_id: int | None = None  # auto-assigned by the manager

    def serialize(self) -> str:
        """Serialize this event to SSE wire format."""
        lines = []
        if self.event_id is not None:
            lines.append(f"id: {self.event_id}")
        lines.append(f"event: {self.event}")
        lines.append(f"data: {json.dumps(self.data, ensure_ascii=False, default=str)}")
        lines.append("")
        return "\n".join(lines)


# ── Manager ──────────────────────────────────────────────────────────


class SSEManager:
    """Manages SSE client subscriptions and event broadcasting.

    Usage:
        manager = SSEManager()

        # In the SSE endpoint:
        async for chunk in manager.subscribe(last_event_id):
            yield chunk

        # When a new RFP ticket is created:
        await manager.broadcast(SSEEvent(event="rfp_ticket_created", data={...}))
    """

    def __init__(self, keepalive_interval: float = 15.0):
        self._subscribers: dict[int, asyncio.Queue[SSEEvent | None]] = {}
        self._next_subscriber_id = 0
        self._event_counter = 0
        self._keepalive_interval = keepalive_interval
        # Ring buffer of recent events for Last-Event-ID replay (max 100)
        self._recent_events: list[SSEEvent] = []
        self._max_replay_events = 100
        self._lock = asyncio.Lock()

    async def subscribe(
        self,
        last_event_id: int | None = None,
    ) -> AsyncGenerator[str, None]:
        """Create a subscription and yield SSE-formatted strings.

        If *last_event_id* is provided, replays any events that were
        broadcast after that id from the ring buffer (catch-up recovery).
        Then streams real-time events until the client disconnects.
        Sends keep-alive comment frames periodically.
        """
        queue: asyncio.Queue[SSEEvent | None] = asyncio.Queue()
        sub_id = self._add_subscriber(queue)

        try:
            # ── Replay missed events (Last-Event-ID recovery) ──────
            if last_event_id is not None:
                async with self._lock:
                    for ev in self._recent_events:
                        if ev.event_id is not None and ev.event_id > last_event_id:
                            yield ev.serialize()

            # ── Stream live events ─────────────────────────────────
            while True:
                try:
                    event = await asyncio.wait_for(
                        queue.get(),
                        timeout=self._keepalive_interval,
                    )
                except asyncio.TimeoutError:
                    # Keep-alive: SSE comment frame
                    yield ": keepalive\n\n"
                    continue

                if event is None:
                    # Sentinel: client disconnected or manager shutting down
                    break

                yield event.serialize()
        finally:
            self._remove_subscriber(sub_id)

    async def broadcast(self, event: SSEEvent) -> None:
        """Broadcast an SSE event to all connected subscribers.

        Assigns an auto-incrementing event_id and stores it in the
        ring buffer for Last-Event-ID replay.
        """
        async with self._lock:
            self._event_counter += 1
            event.event_id = self._event_counter

            # Store in ring buffer
            self._recent_events.append(event)
            if len(self._recent_events) > self._max_replay_events:
                self._recent_events.pop(0)

            # Dispatch to all current subscribers
            dead_subs: list[int] = []
            for sub_id, queue in self._subscribers.items():
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    # Slow consumer — drop and disconnect
                    dead_subs.append(sub_id)
                    logger.warning("SSE subscriber %d dropped (queue full)", sub_id)

            for sub_id in dead_subs:
                self._remove_subscriber(sub_id)

        logger.debug(
            "SSE broadcast event=%s id=%s subscribers=%d",
            event.event,
            event.event_id,
            len(self._subscribers),
        )

    def subscriber_count(self) -> int:
        """Return the number of currently connected clients."""
        return len(self._subscribers)

    def _add_subscriber(self, queue: asyncio.Queue[SSEEvent | None]) -> int:
        sub_id = self._next_subscriber_id
        self._next_subscriber_id += 1
        self._subscribers[sub_id] = queue
        logger.info("SSE subscriber %d connected (total: %d)", sub_id, len(self._subscribers))
        return sub_id

    def _remove_subscriber(self, sub_id: int) -> None:
        self._subscribers.pop(sub_id, None)
        logger.info("SSE subscriber %d disconnected (total: %d)", sub_id, len(self._subscribers))


# ── Singleton ────────────────────────────────────────────────────────

# Module-level singleton — used by both the SSE router and RFP router.
manager = SSEManager()


__all__ = [
    "EVENT_RFP_TICKET_CREATED",
    "EVENT_KPI_THRESHOLD_ALERT",
    "EVENT_SUPPORT_TICKET_ESCALATED",
    "SSEEvent",
    "SSEManager",
    "manager",
]
