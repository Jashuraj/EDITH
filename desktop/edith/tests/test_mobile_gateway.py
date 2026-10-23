"""Unit tests for EDITH Mobile PWA, Gateway, and Tunnel Subsystems."""

import json
import threading
import time
import unittest
import urllib.request
import urllib.error

from edith.phone.gateway import create_phone_gateway
from edith.phone.tunnel import TUNNEL_MANAGER
from edith.ui.server import create_ui_server


class TestMobileAndTunnelSubsystems(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ui_server = create_ui_server(port=8894)
        cls.phone_server = create_phone_gateway(port=8895)
        cls.t_ui = threading.Thread(target=cls.ui_server.serve_forever, daemon=True)
        cls.t_phone = threading.Thread(target=cls.phone_server.serve_forever, daemon=True)
        cls.t_ui.start()
        cls.t_phone.start()
        time.sleep(0.15)

    @classmethod
    def tearDownClass(cls):
        cls.ui_server.shutdown()
        cls.ui_server.server_close()
        cls.phone_server.shutdown()
        cls.phone_server.server_close()

    def test_mobile_index_served(self):
        req = urllib.request.Request("http://127.0.0.1:8894/mobile")
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            content = res.read().decode("utf-8")
            self.assertIn("E.D.I.T.H. Mobile", content)
            self.assertIn("spiderman_logo.svg", content)

    def test_mobile_manifest_served(self):
        req = urllib.request.Request("http://127.0.0.1:8894/mobile/manifest.json")
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            manifest = json.loads(res.read().decode("utf-8"))
            self.assertEqual(manifest["name"], "E.D.I.T.H. Mobile")
            self.assertTrue(len(manifest["icons"]) >= 2)

    def test_mobile_config_endpoint(self):
        req = urllib.request.Request("http://127.0.0.1:8894/mobile/config")
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertIn("local_ip", data)
            self.assertIn("ui_port", data)
            self.assertIn("phone_port", data)

    def test_tunnel_status_and_custom_url(self):
        # 1. Status
        req = urllib.request.Request("http://127.0.0.1:8894/api/tunnel")
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertIn("has_ssh", data)

        # 2. Set Custom Cloud URL
        body = json.dumps({"action": "set_custom", "url": "https://test-edith.trycloudflare.com"}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8894/api/tunnel", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertTrue(data["success"])
            self.assertEqual(data["tunnel_url"], "https://test-edith.trycloudflare.com")

        # Cleanup
        TUNNEL_MANAGER.set_custom_url("")

    def test_phone_ping_endpoint(self):
        req = urllib.request.Request("http://127.0.0.1:8895/ping")
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")

    def test_phone_cmd_execution(self):
        body = json.dumps({"command": "what is your status"}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8895/cmd", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertTrue(data["success"])
            self.assertTrue(data["matched"])
            self.assertIn("EDITH Online", data["result"])

    def test_command_validation_empty(self):
        body = json.dumps({"command": "   "}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8895/cmd", data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=3.0) as res:
                self.assertEqual(res.status, 400)
        except urllib.error.HTTPError as ex:
            self.assertEqual(ex.code, 400)
            with ex:
                err_data = json.loads(ex.read().decode("utf-8"))
            self.assertIn("Empty command", err_data["error"])

    def test_command_validation_too_long(self):
        body = json.dumps({"command": "A" * 1050}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8895/cmd", data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=3.0) as res:
                self.assertEqual(res.status, 400)
        except urllib.error.HTTPError as ex:
            self.assertEqual(ex.code, 400)
            with ex:
                err_data = json.loads(ex.read().decode("utf-8"))
            self.assertIn("exceeds 1000 character limit", err_data["error"])

    def test_emergency_stop_and_resume_from_phone(self):
        # 1. Stop
        body = json.dumps({}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8895/emergency_stop", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertTrue(data["success"])
            self.assertEqual(data["state"], "EMERGENCY_STOP")

        # 2. Resume
        req = urllib.request.Request("http://127.0.0.1:8895/resume", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertTrue(data["success"])
            self.assertEqual(data["state"], "READY")

    def test_phone_root_serves_mobile_pwa(self):
        req = urllib.request.Request("http://127.0.0.1:8895/")
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            content = res.read().decode("utf-8")
            self.assertIn("E.D.I.T.H. Mobile", content)

    def test_phone_vnc_endpoint(self):
        req = urllib.request.Request("http://127.0.0.1:8895/vnc")
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            content = res.read().decode("utf-8")
            self.assertIn("EDITH VNC", content)
            self.assertIn("vnc-canvas", content)

    def test_phone_gateway_mode_endpoint(self):
        req = urllib.request.Request("http://127.0.0.1:8895/api/mode")
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertIn("manual_mode", data)

        body = json.dumps({"mode": "online"}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8895/api/mode", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertEqual(data["manual_mode"], "online")

        # Revert to auto
        body = json.dumps({"mode": "auto"}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8895/api/mode", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)


if __name__ == "__main__":
    unittest.main()
