"""Unit tests for EventBus and StateMachine."""

import asyncio
import tempfile
import unittest
from pathlib import Path

from edith.core.event_bus import Event, EventBus
from edith.core.state_machine import InvalidStateTransitionError, StateMachine, SystemState


class TestEventBus(unittest.IsolatedAsyncioTestCase):
    async def test_publish_and_subscribe(self):
        bus = EventBus()
        received = []

        async def handler(event: Event):
            received.append(event.data.get("msg"))

        bus.subscribe("test:topic", handler)
        await bus.publish("test:topic", {"msg": "hello world"})

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0], "hello world")

    async def test_wildcard_subscriber(self):
        bus = EventBus()
        received_topics = []

        async def wildcard_handler(event: Event):
            received_topics.append(event.topic)

        bus.subscribe("*", wildcard_handler)
        await bus.publish("alpha", {})
        await bus.publish("beta", {})

        self.assertIn("alpha", received_topics)
        self.assertIn("beta", received_topics)


class TestStateMachine(unittest.IsolatedAsyncioTestCase):
    async def test_valid_transitions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = StateMachine(initial_state=SystemState.BOOTING, state_dir=Path(tmpdir))
            self.assertEqual(sm.current_state, SystemState.BOOTING)

            await sm.transition_to(SystemState.READY, reason="Boot sequence done")
            self.assertEqual(sm.current_state, SystemState.READY)

            await sm.transition_to(SystemState.LISTENING, reason="User spoke")
            self.assertEqual(sm.current_state, SystemState.LISTENING)

            # Check mirror file
            state_file = Path(tmpdir) / "state"
            self.assertTrue(state_file.exists())
            self.assertEqual(state_file.read_text(encoding="utf-8"), "listening")

    async def test_invalid_transition_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = StateMachine(initial_state=SystemState.BOOTING, state_dir=Path(tmpdir))
            with self.assertRaises(InvalidStateTransitionError):
                await sm.transition_to(SystemState.VERIFYING, reason="Illegal jump")

    async def test_emergency_stop_always_allowed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = StateMachine(initial_state=SystemState.EXECUTING, state_dir=Path(tmpdir))
            await sm.transition_to(SystemState.EMERGENCY_STOP, reason="Safety pull")
            self.assertEqual(sm.current_state, SystemState.EMERGENCY_STOP)


if __name__ == "__main__":
    unittest.main()
