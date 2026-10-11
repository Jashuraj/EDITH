"""Unit tests for Phone Gateway and Protocol."""

import json
import threading
import time
import unittest
import urllib.request
from edith.phone.gateway import create_phone_gateway
from edith.phone.protocol import PhoneProtocol


class TestPhoneProtocol(unittest.TestCase):
    def test_pairing_and_verification(self):
        proto = PhoneProtocol()
        token = proto.pair_device("dev_01", "Pixel 8")
        self.assertTrue(proto.verify_token("dev_01", token))
        self.assertFalse(proto.verify_token("dev_01", "wrong_token"))

    def test_command_queue(self):
        proto = PhoneProtocol()
        proto.pair_device("dev_01", "Pixel 8")
        qlen = proto.queue_command("dev_01", "prepare release")
        self.assertEqual(qlen, 1)

        item = proto.pop_next_command()
        self.assertIsNotNone(item)
        self.assertEqual(item["command"], "prepare release")


class TestPhoneGatewayServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_phone_gateway(port=8797)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_pair_and_status(self):
        # 1. Pair
        body = json.dumps({"device_id": "test_phone", "device_name": "Test Phone"}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8797/pair", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertTrue(data["paired"])
            token = data["token"]

        # 2. Status
        req = urllib.request.Request("http://127.0.0.1:8797/status")
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)


if __name__ == "__main__":
    unittest.main()
