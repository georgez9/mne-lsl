"""Tests for recording without a GUI or physical LSL hardware."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from lsl_gui.models import DataChunk, StreamDescriptor
from lsl_gui.recording import SessionRecorder, sanitize_name


def make_descriptor(key: str = "stream-1") -> StreamDescriptor:
    return StreamDescriptor(
        key=key,
        name="EEG / Test",
        stype="EEG",
        source_id="source",
        hostname="localhost",
        n_channels=2,
        sfreq=250.0,
        channel_names=("C3", "C4"),
        dtype="float32",
    )


class RecordingTests(unittest.TestCase):
    def test_sanitize_name_removes_windows_unsafe_characters(self) -> None:
        self.assertEqual(sanitize_name(' P01:pre/test* '), "P01_pre_test")

    def test_save_writes_csv_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            recorder = SessionRecorder(Path(directory), "P01", "baseline")
            descriptor = make_descriptor()
            recorder.register_stream(descriptor)
            recorder.append(
                DataChunk(
                    stream_key=descriptor.key,
                    samples=((1.0, 2.0), (3.0, 4.0)),
                    remote_timestamps=(10.0, 11.0),
                    corrected_timestamps=(10.1, 11.1),
                    host_timestamps=(1_700_000_000.0, 1_700_000_001.0),
                )
            )
            saved = recorder.save()
            csv_path = next(saved.glob("*.csv"))
            with csv_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle))
            manifest = json.loads((saved / "session.json").read_text(encoding="utf-8"))
            self.assertEqual(rows[0][-2:], ["C3", "C4"])
            self.assertEqual(len(rows), 3)
            self.assertEqual(manifest["streams"][0]["samples_written"], 2)
            self.assertFalse(any(saved.glob("*.part")))

    def test_malformed_channel_row_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            recorder = SessionRecorder(Path(directory), "P01", "test")
            descriptor = make_descriptor()
            recorder.register_stream(descriptor)
            recorder.append(
                DataChunk(
                    stream_key=descriptor.key,
                    samples=((1.0,),),
                    remote_timestamps=(1.0,),
                    corrected_timestamps=(1.0,),
                    host_timestamps=(1_700_000_000.0,),
                )
            )
            saved = recorder.save()
            with next(saved.glob("*.csv")).open(newline="", encoding="utf-8") as handle:
                self.assertEqual(len(list(csv.reader(handle))), 1)


if __name__ == "__main__":
    unittest.main()
