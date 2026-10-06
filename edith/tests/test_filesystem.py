"""Unit tests for Sandboxed Filesystem Toolpack."""

import tempfile
import unittest
from pathlib import Path

from edith.core.security import SecurityViolationError
from edith.tools.filesystem import FilesystemTools


class TestFilesystemTools(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.jail_root = Path(self.tmpdir.name).resolve()
        self.fs = FilesystemTools(workspace_root=self.jail_root)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_safe_read_write(self):
        write_res = self.fs.write_file("notes/test.txt", "Hello EDITH")
        self.assertTrue(write_res["success"])
        self.assertEqual(write_res["bytes_written"], 11)

        read_res = self.fs.read_file("notes/test.txt")
        self.assertTrue(read_res["success"])
        self.assertEqual(read_res["content"], "Hello EDITH")

    def test_path_traversal_blocked(self):
        with self.assertRaises(SecurityViolationError):
            self.fs.read_file("../../Windows/System32/drivers/etc/hosts")

    def test_list_and_delete(self):
        self.fs.write_file("file1.txt", "abc")
        self.fs.write_file("file2.txt", "def")

        list_res = self.fs.list_dir(".")
        self.assertTrue(list_res["success"])
        names = [e["name"] for e in list_res["entries"]]
        self.assertIn("file1.txt", names)
        self.assertIn("file2.txt", names)

        del_res = self.fs.delete_file("file1.txt")
        self.assertTrue(del_res["success"])
        self.assertFalse((self.jail_root / "file1.txt").exists())


if __name__ == "__main__":
    unittest.main()
