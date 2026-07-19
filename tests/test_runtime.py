"""Tests for runtime paths used by source and packaged builds."""

from __future__ import annotations

import unittest
from os import environ
from pathlib import Path
from unittest.mock import patch

from lsl_gui.runtime import default_recording_directory, user_data_root


class RuntimeTests(unittest.TestCase):
    @patch("lsl_gui.runtime.is_frozen", return_value=True)
    @patch("lsl_gui.runtime.Path.home", return_value=Path("C:/Users/Test"))
    def test_frozen_data_uses_user_documents(self, _home: object, _frozen: object) -> None:
        self.assertEqual(
            user_data_root(),
            Path("C:/Users/Test/Documents/LSL Recorder"),
        )
        self.assertEqual(
            default_recording_directory(),
            Path("C:/Users/Test/Documents/LSL Recorder/Data"),
        )

    def test_environment_overrides_recording_directory(self) -> None:
        """Allow administrators and portable setups to choose a data location."""

        original = environ.get("LSL_RECORDER_DATA_DIR")
        environ["LSL_RECORDER_DATA_DIR"] = "custom-data"
        try:
            self.assertEqual(default_recording_directory(), Path("custom-data"))
        finally:
            if original is None:
                environ.pop("LSL_RECORDER_DATA_DIR", None)
            else:
                environ["LSL_RECORDER_DATA_DIR"] = original


if __name__ == "__main__":
    unittest.main()
