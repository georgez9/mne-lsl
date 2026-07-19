"""Tests for the packaged application launcher."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from build_tools.launcher import main


class LauncherTests(unittest.TestCase):
    def test_smoke_failure_returns_nonzero_and_writes_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "smoke.txt"
            with (
                patch.dict(
                    os.environ,
                    {"LSL_RECORDER_SMOKE_REPORT": str(report)},
                ),
                patch("build_tools.launcher.sys.argv", ["launcher", "--smoke-test"]),
                patch(
                    "build_tools.launcher._smoke_test",
                    side_effect=ImportError("native DLL missing"),
                ),
            ):
                self.assertEqual(main(), 1)
            self.assertIn("native DLL missing", report.read_text(encoding="utf-8"))

    def test_smoke_success_returns_zero_and_writes_ok(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "smoke.txt"
            with (
                patch.dict(
                    os.environ,
                    {"LSL_RECORDER_SMOKE_REPORT": str(report)},
                ),
                patch("build_tools.launcher.sys.argv", ["launcher", "--smoke-test"]),
                patch("build_tools.launcher._smoke_test"),
            ):
                self.assertEqual(main(), 0)
            self.assertEqual(report.read_text(encoding="utf-8"), "OK\n")


if __name__ == "__main__":
    unittest.main()
