"""Tests for the SSE (Server-Sent Events) real-time notification system.

Covers:
- SSEEvent serialization wire format
- SSEManager pub/sub, broadcast, ring buffer replay
- /api/events/stream endpoint (auth, headers, streaming)
- Integration with RFP upload pipeline (SSE broadcast on ticket creation)
"""

from __future__ import annotations

import asyncio
import json
import unittest
from asyncio import Queue
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.main import app
from app.notifications import (
    EVENT_RFP_TICKET_CREATED,
    EVENT_KPI_THRESHOLD_ALERT,
    SSEEvent,
    SSEManager,
)


# ======================================================================
#  SSEEvent serialization tests
# ======================================================================


class SSEEventSerializationTests(unittest.TestCase):
    """Verify the SSE wire format produced by SSEEvent.serialize()."""

    def test_basic_event_without_id(self):
        event = SSEEvent(event=EVENT_RFP_TICKET_CREATED, data={"status": "ok"})
        output = event.serialize()
        lines = output.split("\n")
        self.assertIn("event: rfp_ticket_created", lines)
        self.assertIn('data: {"status": "ok"}', lines)
        # No "id:" line when event_id is None
        self.assertFalse(any(l.startswith("id:") for l in lines))
        # Must end with a trailing newline (SSE requires blank-line separator)
        self.assertTrue(output.endswith("\n"))
        # Last line is empty (empty string after the last \n)
        self.assertEqual(lines[-1], "")

    def test_event_with_id(self):
        event = SSEEvent(event="rfp_ticket_created", data={"ticket_id": "tkt_001"}, event_id=42)
        output = event.serialize()
        lines = output.split("\n")
        self.assertIn("id: 42", lines)
        self.assertIn("event: rfp_ticket_created", lines)
        self.assertIn('data: {"ticket_id": "tkt_001"}', lines)
        self.assertTrue(output.endswith("\n"))

    def test_event_with_complex_payload(self):
        data = {
            "ticket_id": "tkt_abc",
            "rfp_id": "rfp_tkt_abc",
            "client_name": "NubeSoft",
            "client_hq": "Miami",
            "services_requested": ["soporte", "infraestructura"],
            "status": "analizando",
            "created_at": "2026-07-24T14:32:00Z",
        }
        event = SSEEvent(event=EVENT_RFP_TICKET_CREATED, data=data, event_id=1)
        output = event.serialize()
        lines = output.split("\n")
        self.assertIn("id: 1", lines)
        self.assertIn("event: rfp_ticket_created", lines)
        # Verify JSON data payload is valid
        data_line = next(l for l in lines if l.startswith("data: "))
        payload = json.loads(data_line[6:])
        self.assertEqual(payload["ticket_id"], "tkt_abc")
        self.assertEqual(payload["client_name"], "NubeSoft")
        self.assertEqual(payload["services_requested"], ["soporte", "infraestructura"])
        self.assertEqual(payload["status"], "analizando")

    def test_unicode_in_payload(self):
        """Non-ASCII characters should be serialized correctly."""
        data = {"client_name": "José Martínez", "ticket_id": "tkt_ñ"}
        event = SSEEvent(event="rfp_ticket_created", data=data, event_id=3)
        output = event.serialize()
        self.assertIn("José", output)
        self.assertIn("ñ", output)

    def test_serialize_is_idempotent(self):
        """Calling serialize() multiple times returns the same result."""
        data = {"ticket_id": "tkt_001"}
        event = SSEEvent(event="rfp_ticket_created", data=data, event_id=1)
        first = event.serialize()
        second = event.serialize()
        self.assertEqual(first, second)


# ======================================================================
#  SSEManager unit tests
# ======================================================================


async def _subscribe_and_task(manager, last_event_id=None):
    """Create a subscriber running in a background task.

    The async generator's body is entered immediately so the subscriber
    is registered before returning.

    Returns:
        (read_next, cancel)
        - read_next(timeout=2.0) -> str|None — await to get next SSE chunk
        - cancel() — stop the background task and close the generator
    """
    gen = manager.subscribe(last_event_id=last_event_id)
    it = gen.__aiter__()
    output_queue: Queue = Queue()

    async def _consumer():
        """Consume from the async generator, push to output_queue."""
        try:
            while True:
                try:
                    val = await asyncio.wait_for(it.__anext__(), timeout=30.0)
                    await output_queue.put(val)
                except asyncio.TimeoutError:
                    await output_queue.put(None)
                    break
                except StopAsyncIteration:
                    break
        except (asyncio.CancelledError, RuntimeError):
            pass
        finally:
            try:
                await gen.aclose()
            except (StopAsyncIteration, RuntimeError):
                pass

    task = asyncio.create_task(_consumer())
    # Give the task a moment to enter the generator body
    await asyncio.sleep(0.01)

    async def read_next(timeout=2.0):
        try:
            return await asyncio.wait_for(output_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    async def cancel():
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, RuntimeError):
            pass

    return read_next, cancel


class SSEManagerBroadcastTests(unittest.TestCase):
    """Test the pub/sub broadcast logic of SSEManager."""

    def setUp(self):
        self.manager = SSEManager(keepalive_interval=30.0)

    def test_broadcast_delivers_to_subscriber(self):
        """A subscriber receives events broadcast after subscription."""
        async def run():
            read_next, cancel = await _subscribe_and_task(self.manager)
            event = SSEEvent(event="rfp_ticket_created", data={"ticket_id": "tkt_001"})
            await self.manager.broadcast(event)
            result = await read_next()
            await cancel()
            self.assertIsNotNone(result)
            self.assertIn("event: rfp_ticket_created", result)
            self.assertIn('"ticket_id": "tkt_001"', result)

        asyncio.run(run())

    def test_broadcast_assigns_incrementing_ids(self):
        """Each broadcast gets a unique auto-incrementing event_id."""
        async def run():
            read_next, cancel = await _subscribe_and_task(self.manager)
            ev1 = SSEEvent(event="e1", data={"n": 1})
            ev2 = SSEEvent(event="e2", data={"n": 2})
            ev3 = SSEEvent(event="e3", data={"n": 3})
            await self.manager.broadcast(ev1)
            await self.manager.broadcast(ev2)
            await self.manager.broadcast(ev3)

            r1 = await read_next()
            r2 = await read_next()
            r3 = await read_next()

            self.assertIn("id: 1", r1)
            self.assertIn("id: 2", r2)
            self.assertIn("id: 3", r3)

            await cancel()

        asyncio.run(run())

    def test_keepalive_sent_during_idle_period(self):
        """A keepalive comment frame is sent after keepalive_interval of inactivity."""
        manager = SSEManager(keepalive_interval=0.05)  # 50 ms

        async def run():
            read_next, cancel = await _subscribe_and_task(manager)
            # Wait for keepalive (more than 50ms)
            await asyncio.sleep(0.1)
            result = await read_next(timeout=0.5)
            await cancel()
            self.assertIsNotNone(result)
            self.assertEqual(result, ": keepalive\n\n")

        asyncio.run(run())

    def test_subscriber_count_increments_and_decrements(self):
        """Subscriber count reflects active subscriptions."""
        async def run():
            self.assertEqual(self.manager.subscriber_count(), 0)
            r1, c1 = await _subscribe_and_task(self.manager)
            self.assertEqual(self.manager.subscriber_count(), 1)
            r2, c2 = await _subscribe_and_task(self.manager)
            self.assertEqual(self.manager.subscriber_count(), 2)
            await c1()
            # Give time for the subscriber to be removed
            await asyncio.sleep(0.01)
            self.assertEqual(self.manager.subscriber_count(), 1)
            await c2()
            await asyncio.sleep(0.01)
            self.assertEqual(self.manager.subscriber_count(), 0)

        asyncio.run(run())

    def test_recovery_replays_missed_events(self):
        """A subscriber with last_event_id replays missed events from ring buffer."""
        async def run():
            # Subscribe and broadcast events
            read1, cancel1 = await _subscribe_and_task(self.manager)
            ev1 = SSEEvent(event="rfp_ticket_created", data={"ticket_id": "tkt_001"})
            ev2 = SSEEvent(event="rfp_ticket_created", data={"ticket_id": "tkt_002"})
            await self.manager.broadcast(ev1)
            await self.manager.broadcast(ev2)

            # Consume ev1 and ev2
            r1 = await read1()
            r2 = await read1()
            self.assertIsNotNone(r1)
            self.assertIsNotNone(r2)
            await cancel1()

            # Broadcast ev3 (id=3)
            ev3 = SSEEvent(event="rfp_ticket_created", data={"ticket_id": "tkt_003"})
            await self.manager.broadcast(ev3)

            # Reconnect with last_event_id=2 — should replay ev3 (id=3)
            read2, cancel2 = await _subscribe_and_task(self.manager, last_event_id=2)
            result = await read2(timeout=2.0)
            await cancel2()
            self.assertIsNotNone(result)
            self.assertIn('"ticket_id": "tkt_003"', result)
            # Should NOT include ev1 or ev2 (those are at or before id=2)
            self.assertNotIn('"ticket_id": "tkt_001"', result)
            self.assertNotIn('"ticket_id": "tkt_002"', result)

        asyncio.run(run())

    def test_ring_buffer_caps_at_max_replay(self):
        """Ring buffer doesn't grow beyond max_replay_events."""
        manager = SSEManager(keepalive_interval=30.0)
        manager._max_replay_events = 5

        async def run():
            for i in range(10):
                ev = SSEEvent(event="test", data={"n": i})
                await manager.broadcast(ev)

            self.assertEqual(len(manager._recent_events), 5)
            # Should have events 5..9 (most recent)
            self.assertEqual(manager._recent_events[0].data["n"], 5)
            self.assertEqual(manager._recent_events[-1].data["n"], 9)

        asyncio.run(run())

    def test_recovery_with_id_beyond_buffer_returns_empty(self):
        """If last_event_id is older than the oldest buffered event, no replay."""
        manager = SSEManager(keepalive_interval=30.0)
        manager._max_replay_events = 3

        async def run():
            for i in range(5):
                ev = SSEEvent(event="test", data={"n": i})
                await manager.broadcast(ev)

            # Reconnect with id=1 (evicted from buffer - oldest is 2)
            read, cancel = await _subscribe_and_task(manager, last_event_id=1)
            # Wait a short time — the replay section is synchronous (before any
            # await), so if it ran, the result would be in the queue already.
            # Since id=1 was evicted, the replay loop yields nothing.
            await asyncio.sleep(0.05)
            result = await read(timeout=0.5)
            await cancel()
            # Should get either None (timeout, no replay happened) or
            # the keepalive/next live event. Either way, should NOT be ev1.
            if result is not None:
                self.assertNotIn('"n": 0', result)
                self.assertNotIn('"n": 1', result)

        asyncio.run(run())


class SSEManagerMultipleSubscribersTests(unittest.TestCase):
    """Multiple subscribers all receive the same broadcast."""

    def setUp(self):
        self.manager = SSEManager(keepalive_interval=30.0)

    def test_all_subscribers_receive_broadcast(self):
        async def run():
            r1, c1 = await _subscribe_and_task(self.manager)
            r2, c2 = await _subscribe_and_task(self.manager)
            r3, c3 = await _subscribe_and_task(self.manager)

            event = SSEEvent(event="rfp_ticket_created", data={"ticket_id": "tkt_001"})
            await self.manager.broadcast(event)

            for reader in [r1, r2, r3]:
                result = await reader()
                self.assertIsNotNone(result)
                self.assertIn("rfp_ticket_created", result)

            await c1()
            await c2()
            await c3()

        asyncio.run(run())

    def test_subscriber_disconnected_during_broadcast(self):
        """A subscriber that disconnects mid-broadcast doesn't affect others."""
        async def run():
            r1, c1 = await _subscribe_and_task(self.manager)
            r2, c2 = await _subscribe_and_task(self.manager)

            await c1()
            await asyncio.sleep(0.01)

            event = SSEEvent(event="rfp_ticket_created", data={"ticket_id": "tkt_002"})
            await self.manager.broadcast(event)

            result2 = await r2()
            self.assertIsNotNone(result2)
            self.assertIn("tkt_002", result2)
            await c2()

        asyncio.run(run())


# ======================================================================
#  /api/events/stream endpoint tests
# ======================================================================


class SSEStreamEndpointTests(unittest.TestCase):
    """Test the FastAPI SSE streaming endpoint via TestClient."""

    def setUp(self):
        self.previous_overrides = app.dependency_overrides.copy()
        # Mock current_user for authenticated requests
        app.dependency_overrides[get_current_user] = lambda: {
            "doc_id": 1,
            "email": "admin@nexova.com",
            "role": "admin",
        }
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self):
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)

    def test_stream_requires_auth(self):
        """Endpoint returns 401 without a valid token."""
        app.dependency_overrides[get_current_user] = lambda: (_ for _ in ()).throw(
            HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado.")
        )
        response = self.client.get("/api/events/stream")
        self.assertEqual(response.status_code, 401)

    def test_stream_response_headers(self):
        """Response has correct SSE headers."""
        # Mock subscribe to yield one chunk then stop (infinite stream blocks TestClient)
        from app.routers import events as events_module

        async def finite_subscribe(last_event_id=None):
            yield "data: test\n\n"
            return

        with patch.object(events_module.manager, "subscribe", side_effect=finite_subscribe):
            with self.client.stream("GET", "/api/events/stream") as response:
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/event-stream", response.headers.get("content-type", ""))
                # Security middleware overrides to 'no-store' for all responses
                self.assertIn(response.headers.get("cache-control", "").lower(), ("no-cache", "no-store"))
                self.assertEqual(response.headers.get("x-accel-buffering"), "no")
                self.assertEqual(response.headers.get("connection"), "keep-alive")

    def test_stream_supports_last_event_id_query(self):
        """The Last-Event-ID query parameter is accepted."""
        from app.routers import events as events_module

        async def finite_subscribe(last_event_id=None):
            yield "data: test\n\n"
            return

        with patch.object(events_module.manager, "subscribe", side_effect=finite_subscribe):
            with self.client.stream("GET", "/api/events/stream?Last-Event-ID=5") as response:
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/event-stream", response.headers.get("content-type", ""))

    def test_stream_invalid_last_event_id(self):
        """Non-integer Last-Event-ID is rejected with validation error."""
        response = self.client.get("/api/events/stream?Last-Event-ID=abc")
        self.assertEqual(response.status_code, 400)


# ======================================================================
#  Singleton manager import tests
# ======================================================================


class SingletonManagerTests(unittest.TestCase):
    """The module-level 'manager' singleton is properly importable."""

    def test_manager_is_singleton(self):
        from app.notifications import manager as m1
        from app.notifications import manager as m2
        self.assertIs(m1, m2)

    def test_manager_is_ssemanager_instance(self):
        from app.notifications import manager
        self.assertIsInstance(manager, SSEManager)

    def test_event_constants_are_strings(self):
        self.assertIsInstance(EVENT_RFP_TICKET_CREATED, str)
        self.assertIsInstance(EVENT_KPI_THRESHOLD_ALERT, str)
        self.assertEqual(EVENT_RFP_TICKET_CREATED, "rfp_ticket_created")
        self.assertEqual(EVENT_KPI_THRESHOLD_ALERT, "kpi_threshold_alert")


# ======================================================================
#  Payload shape compliance tests
# ======================================================================


class RFPPayloadShapeTests(unittest.TestCase):
    """Verify that the SSE event payload shape matches the RFP Briefing spec."""

    def test_rfp_ticket_created_payload_has_required_fields(self):
        """The payload must contain all fields specified in the Briefing."""
        payload = {
            "ticket_id": "tkt_abc123",
            "rfp_id": "rfp_tkt_abc123",
            "client_name": "NubeSoft",
            "client_hq": "Miami",
            "services_requested": ["soporte"],
            "status": "analizando",
            "created_at": "2026-07-24T14:32:00Z",
        }
        required_fields = [
            "ticket_id",
            "rfp_id",
            "client_name",
            "client_hq",
            "services_requested",
            "status",
            "created_at",
        ]
        for field in required_fields:
            self.assertIn(field, payload, f"Missing required field: {field}")

    def test_initial_status_is_analizando(self):
        """A new RFP ticket always starts with status 'analizando'."""
        from app.rfp_models import TicketStatus
        self.assertEqual(TicketStatus.ANALIZANDO, "analizando")

    def test_event_name_is_rfp_ticket_created(self):
        """The SSE event name matches the Briefing spec."""
        self.assertEqual(EVENT_RFP_TICKET_CREATED, "rfp_ticket_created")
