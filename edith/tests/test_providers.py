"""Unit tests for Model Provider Abstraction and Circuit Breaker."""

import unittest
from edith.providers.base import CircuitBreaker, CircuitState, ModelResponse, ToolCall


class TestCircuitBreaker(unittest.TestCase):
    def test_circuit_trips_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.1)
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertTrue(cb.can_execute())

        cb.record_failure("error 1")
        self.assertEqual(cb.state, CircuitState.CLOSED)
        cb.record_failure("error 2")
        self.assertEqual(cb.state, CircuitState.CLOSED)
        cb.record_failure("error 3")
        self.assertEqual(cb.state, CircuitState.OPEN)
        self.assertFalse(cb.can_execute())

    def test_circuit_resets_on_success(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure("error 1")
        cb.record_success()
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertTrue(cb.can_execute())


if __name__ == "__main__":
    unittest.main()
