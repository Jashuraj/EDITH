"""Unit tests for Gateway Compatibility Endpoints in the EDITH UI Server."""

import json
import threading
import time
import unittest
import urllib.request
from edith.ui.server import create_ui_server


class TestGatewayUIAirlock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_ui_server(port=8799)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _get(self, path: str):
        req = urllib.request.Request(f"http://127.0.0.1:8799{path}")
        with urllib.request.urlopen(req, timeout=3.0) as res:
            return res.status, json.loads(res.read().decode("utf-8"))

    def _post(self, path: str, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:8799{path}",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=3.0) as res:
            return res.status, json.loads(res.read().decode("utf-8"))

    def _delete(self, path: str):
        req = urllib.request.Request(f"http://127.0.0.1:8799{path}", method="DELETE")
        with urllib.request.urlopen(req, timeout=3.0) as res:
            return res.status, json.loads(res.read().decode("utf-8"))

    def test_auth_session(self):
        """Verify auth session returns owner=true so desktop HUD doesn't prompt password."""
        status, data = self._get("/api/auth/session")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("owner"))
        self.assertTrue(data.get("configured"))

    def test_metrics_gateway_format(self):
        """Verify /api/metrics has required gateway fields."""
        status, data = self._get("/api/metrics")
        self.assertEqual(status, 200)
        self.assertIn("cpu_percent", data)
        self.assertIn("ram_percent", data)
        self.assertIn("battery_percent", data)
        self.assertIn("host_online", data)
        self.assertTrue(data["host_online"])

    def test_weather_endpoint_compatibility(self):
        """Verify weather endpoint has available boolean and numeric temp."""
        status, data = self._get("/weather")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("available"))
        self.assertIsInstance(data.get("temp"), int)

    def test_reminders_crud_endpoints(self):
        """Verify reminders list, create, and delete endpoints."""
        status, data = self._post("/api/reminders", {"title": "Test web reminder", "priority": "high"})
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        rem_id = data["reminder"]["id"]

        status, rem_list = self._get("/api/reminders")
        self.assertEqual(status, 200)
        found = [r for r in rem_list.get("reminders", []) if r["id"] == rem_id]
        self.assertEqual(len(found), 1)

        del_status, del_data = self._delete(f"/api/reminders/{rem_id}")
        self.assertEqual(del_status, 200)
        self.assertTrue(del_data.get("ok"))

    def test_calendar_and_holidays_endpoint(self):
        """Verify calendar events and Indian holidays combined response."""
        status, data = self._get("/api/calendar?from=2026-01-01&to=2026-12-31")
        self.assertEqual(status, 200)
        self.assertIn("events", data)
        self.assertIn("holidays", data)
        self.assertIn("holiday_source", data)
        self.assertTrue(len(data["holidays"]) >= 3)

    def test_profile_endpoints(self):
        """Verify profile GET and POST round-trip."""
        status, data = self._get("/api/profile")
        self.assertEqual(status, 200)
        self.assertIn("profile", data)
        self.assertIn("timezone", data["profile"])

        post_status, post_data = self._post("/api/profile", {"city": "New Delhi"})
        self.assertEqual(post_status, 200)
        self.assertEqual(post_data["profile"]["city"], "New Delhi")

    def test_devices_and_pair_code(self):
        """Verify devices query and pairing code generation."""
        status, data = self._get("/api/devices")
        self.assertEqual(status, 200)
        self.assertIn("hosts", data)
        self.assertIn("devices", data)

        code_status, code_data = self._post("/api/pair/code", {"name": "Phone"})
        self.assertEqual(code_status, 200)
        self.assertTrue(code_data.get("ok"))
        self.assertEqual(len(code_data.get("code", "")), 6)
