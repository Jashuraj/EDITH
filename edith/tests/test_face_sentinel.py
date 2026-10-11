"""Unit tests for Biometric Face Presence Sentinel."""

import time
import unittest
from unittest.mock import MagicMock, patch
from edith.tools.face_sentinel import BiometricFaceSentinel, FACE_SENTINEL


class TestFaceSentinel(unittest.TestCase):

    def setUp(self):
        self.sentinel = BiometricFaceSentinel(absence_timeout=10.0)

    def tearDown(self):
        if self.sentinel.is_active:
            self.sentinel.stop()

    def test_singleton_exists(self):
        self.assertIsNotNone(FACE_SENTINEL)
        self.assertTrue(hasattr(FACE_SENTINEL, "start"))
        self.assertTrue(hasattr(FACE_SENTINEL, "stop"))

    def test_start_and_stop_lifecycle(self):
        self.sentinel.simulate_presence(True)
        res_start = self.sentinel.start(absence_timeout=15.0)
        self.assertTrue(res_start["success"])
        self.assertTrue(self.sentinel.is_active)

        status = self.sentinel.get_status()
        self.assertTrue(status["active"])
        self.assertEqual(status["absence_timeout"], 15.0)

        res_stop = self.sentinel.stop()
        self.assertTrue(res_stop["success"])
        self.assertFalse(self.sentinel.is_active)

    def test_timeout_adjustment(self):
        res = self.sentinel.set_timeout(45.0)
        self.assertTrue(res["success"])
        self.assertEqual(self.sentinel.absence_timeout, 45.0)

        # Minimum clamp to 5.0 seconds
        res_min = self.sentinel.set_timeout(1.0)
        self.assertEqual(self.sentinel.absence_timeout, 5.0)

    def test_mock_presence_and_absence_trigger(self):
        self.sentinel.absence_timeout = 5.0
        self.sentinel.simulate_presence(True)
        self.sentinel.start()

        # Simulate presence
        status = self.sentinel.get_status()
        self.assertTrue(status["face_detected"])

        # Simulate absence
        with patch.object(self.sentinel, "_trigger_workstation_lock") as mock_lock:
            self.sentinel.simulate_presence(False)
            # Wind back last seen time to trigger timeout
            self.sentinel._last_seen_time = time.time() - 10.0
            time.sleep(1.2)  # Wait for 1 sentinel loop iteration
            mock_lock.assert_called()


if __name__ == "__main__":
    unittest.main()
