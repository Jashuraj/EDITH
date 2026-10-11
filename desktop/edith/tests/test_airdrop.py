"""Unit tests for Seamless Clipboard and AirDrop Gateway."""

import tempfile
import unittest
from pathlib import Path
from edith.tools.airdrop import AirDropGateway, AIRDROP


class TestAirDropGateway(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.gateway = AirDropGateway(transfer_dir=Path(self.temp_dir.name))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_singleton_exists(self):
        self.assertIsNotNone(AIRDROP)
        self.assertTrue(hasattr(AIRDROP, "get_clipboard_text"))
        self.assertTrue(hasattr(AIRDROP, "set_clipboard_text"))

    def test_clipboard_set_and_get(self):
        test_msg = "EDITH-AIRDROP-TEST-MESSAGE-12345"
        ok = self.gateway.set_clipboard_text(test_msg, source="unit_test")
        self.assertTrue(ok)
        val = self.gateway.get_clipboard_text()
        self.assertEqual(val, test_msg)

    def test_save_and_retrieve_file(self):
        filename = "test_doc.txt"
        content = b"Holographic EDITH AirDrop data stream."
        res = self.gateway.save_uploaded_file(filename, content)
        self.assertTrue(res["success"])
        self.assertEqual(res["size_bytes"], len(content))

        retrieved = self.gateway.get_file_bytes(res["filename"])
        self.assertEqual(retrieved, content)

    def test_filename_sanitization(self):
        dirty_name = "../../../evil_script.sh"
        res = self.gateway.save_uploaded_file(dirty_name, b"safe bytes")
        self.assertTrue(res["success"])
        self.assertNotIn("..", res["filename"])
        self.assertTrue((Path(self.temp_dir.name) / res["filename"]).exists())

    def test_list_shared_files(self):
        self.gateway.save_uploaded_file("file1.dat", b"123")
        self.gateway.save_uploaded_file("file2.dat", b"45678")
        files = self.gateway.list_shared_files()
        self.assertEqual(len(files), 2)
        filenames = [f["filename"] for f in files]
        self.assertIn("file1.dat", filenames)
        self.assertIn("file2.dat", filenames)


if __name__ == "__main__":
    unittest.main()
