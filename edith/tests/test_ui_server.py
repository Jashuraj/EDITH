"""Unit tests for EDITH Local UI Server."""

import json
import threading
import time
import unittest
import urllib.request
from edith.core.state_machine import STATE, SystemState
from edith.ui.server import create_ui_server


class TestUIServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_ui_server(port=8796)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_get_state_endpoint(self):
        req = urllib.request.Request("http://127.0.0.1:8796/state")
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertIn("state", data)
            self.assertIn("emergency_stopped", data)

    def test_post_reflex_cmd(self):
        body = json.dumps({"command": "what is your status"}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8796/cmd", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertTrue(data["matched"])
            self.assertIn("EDITH Online", data["result"])

    def test_get_telemetry_endpoint(self):
        req = urllib.request.Request("http://127.0.0.1:8796/telemetry")
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertIn("runtime_status", data)
            self.assertIn("is_online", data)
            self.assertIn("cpu", data)

    def test_voice_speak_endpoint(self):
        body = json.dumps({"text": "System operational."}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8796/voice/speak", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertIn("success", data)


    def test_get_models_endpoint(self):
        req = urllib.request.Request("http://127.0.0.1:8796/models")
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertIn("models", data)
            self.assertIn("active_model", data)

    def test_post_switch_model_endpoint(self):
        body = json.dumps({"model": "llama3.2:1b"}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8796/models/switch", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertTrue(data["success"])
            self.assertEqual(data["active_model"], "llama3.2:1b")

    def test_mode_endpoints(self):
        # GET mode
        req = urllib.request.Request("http://127.0.0.1:8796/api/mode")
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertIn("manual_mode", data)
            self.assertIn("is_online", data)

        # POST mode switch to online
        body = json.dumps({"mode": "online"}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8796/api/mode", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertEqual(data["manual_mode"], "online")

        # POST mode switch back to auto
        body = json.dumps({"mode": "auto"}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8796/api/mode", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertEqual(data["manual_mode"], "auto")

    def test_logs_endpoint(self):
        req = urllib.request.Request("http://127.0.0.1:8796/api/logs?lines=5")
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertIn("logs", data)
            self.assertIn("count", data)

    def test_mouse_endpoint(self):
        body = json.dumps({"action": "move", "x": 0.5, "y": 0.5}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8796/api/mouse", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertTrue(data["success"])

    def test_mobile_redirect(self):
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        opener = urllib.request.build_opener(NoRedirect)
        try:
            res = opener.open("http://127.0.0.1:8796/mobile")
            self.assertEqual(res.status, 200)
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 302)
            self.assertEqual(e.headers.get("Location"), "/mobile/")


if __name__ == "__main__":
    unittest.main()
