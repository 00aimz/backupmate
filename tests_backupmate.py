import json
import os
import subprocess
import sys
import tempfile
import unittest

import backup_core
import backupmate
from backup_core import run_backup


class BackupCoreTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.src = os.path.join(self.tempdir.name, "src")
        self.dest = os.path.join(self.tempdir.name, "dest")
        os.makedirs(self.src)
        os.makedirs(self.dest)

    def tearDown(self):
        self.tempdir.cleanup()

    def _write_file(self, relative: str, content: str) -> str:
        path = os.path.join(self.src, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_initial_full_backup(self):
        self._write_file("a.txt", "hello")
        self._write_file("nested/b.txt", "world")

        stats = run_backup(self.src, self.dest, mode="full")

        self.assertEqual(stats.files_copied, 2)
        self.assertEqual(stats.skipped, 0)
        self.assertTrue(os.path.exists(os.path.join(self.dest, "a.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.dest, "nested", "b.txt")))

    def test_incremental_skips_unchanged(self):
        self._write_file("a.txt", "hello")
        run_backup(self.src, self.dest, mode="full")

        stats = run_backup(self.src, self.dest, mode="incremental")

        self.assertEqual(stats.files_copied, 0)
        self.assertEqual(stats.skipped, 1)

    def test_exclude_patterns(self):
        self._write_file("skip.log", "ignore")
        self._write_file("keep.txt", "save")

        run_backup(self.src, self.dest, mode="full", excludes=["*.log"])

        self.assertFalse(os.path.exists(os.path.join(self.dest, "skip.log")))
        self.assertTrue(os.path.exists(os.path.join(self.dest, "keep.txt")))

    def test_state_file_read_write(self):
        self._write_file("file.txt", "v1")
        stats_first = run_backup(self.src, self.dest, mode="full")
        self.assertEqual(stats_first.files_copied, 1)

        state_path = os.path.join(self.dest, ".backupmate_state.json")
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("files", data)
        self.assertIn("file.txt", data["files"])

        stats_second = run_backup(self.src, self.dest, mode="incremental")
        self.assertEqual(stats_second.skipped, 1)


class BackupCliTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.src = os.path.join(self.tempdir.name, "src")
        self.dest = os.path.join(self.tempdir.name, "dest")
        os.makedirs(self.src)
        os.makedirs(self.dest)

    def tearDown(self):
        self.tempdir.cleanup()

    def _write_file(self, name: str, content: str):
        path = os.path.join(self.src, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def test_cli_full_backup(self):
        self._write_file("sample.txt", "cli")
        cmd = [sys.executable, "backupmate.py", self.src, self.dest, "--mode", "full"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("sample.txt", os.listdir(self.dest))

    def test_cli_invalid_mode(self):
        cmd = [sys.executable, "backupmate.py", self.src, self.dest, "--mode", "bad"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, backupmate.EXIT_INVALID_ARGS)


if __name__ == "__main__":
    unittest.main()
