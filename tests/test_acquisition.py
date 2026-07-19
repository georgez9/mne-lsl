"""Headless worker tests using an injected fake LSL inlet."""

from __future__ import annotations

import queue
import time
import unittest
from typing import Any

import numpy as np

from lsl_gui.acquisition import StreamWorker
from lsl_gui.models import AcquisitionConfig, DataChunk, StreamDescriptor, StreamState


class FakeInlet:
    last_max_buffered: object | None = None

    def __init__(self, _sinfo: object, **_kwargs: object) -> None:
        self.sinfo = _sinfo
        FakeInlet.last_max_buffered = _kwargs.get("max_buffered")
        self.closed = False
        self.returned = False

    def open_stream(self, timeout: float) -> None:
        del timeout

    def time_correction(self, timeout: float) -> float:
        del timeout
        return 0.5

    def get_sinfo(self, timeout: float) -> object:
        del timeout
        return self.sinfo

    def pull_chunk(self, timeout: float, max_samples: int) -> tuple[list[list[float]], list[float]]:
        del timeout, max_samples
        if not self.returned:
            self.returned = True
            return np.asarray([[1.0, 2.0]]), np.asarray([100.0])
        time.sleep(0.005)
        return np.empty((0, 2)), np.asarray([])

    def close_stream(self) -> None:
        self.closed = True


class FakeRecorder:
    def __init__(self) -> None:
        self.chunks: list[DataChunk] = []

    def append(self, chunk: DataChunk) -> None:
        self.chunks.append(chunk)


class FakeStreamInfo:
    uid = "uid"
    name = "test"
    stype = "EEG"
    source_id = "source"
    hostname = "host"
    n_channels = 2
    sfreq = 100.0
    dtype = "float32"

    def get_channel_names(self) -> list[str]:
        return ["a", "b"]


class AcquisitionTests(unittest.TestCase):
    def test_worker_connects_reads_and_disconnects(self) -> None:
        descriptor = StreamDescriptor(
            key="key",
            name="test",
            stype="EEG",
            source_id="source",
            hostname="host",
            n_channels=2,
            sfreq=100.0,
            channel_names=("a", "b"),
            dtype="float32",
        )
        events: queue.Queue[tuple[str, str, Any]] = queue.Queue()
        worker = StreamWorker(
            descriptor,
            FakeStreamInfo(),
            AcquisitionConfig(pull_timeout=0.01),
            lambda key, event, payload: events.put((key, event, payload)),
            inlet_factory=FakeInlet,
        )
        recorder = FakeRecorder()
        worker.connect()
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            try:
                _, event, payload = events.get(timeout=0.05)
            except queue.Empty:
                continue
            if event == "state" and payload == StreamState.CONNECTED:
                break
        worker.start_reading(recorder)
        deadline = time.monotonic() + 1.0
        while not recorder.chunks and time.monotonic() < deadline:
            time.sleep(0.01)
        worker.disconnect()
        self.assertEqual(len(recorder.chunks), 1)
        self.assertEqual(recorder.chunks[0].corrected_timestamps, (100.5,))
        self.assertEqual(FakeInlet.last_max_buffered, 360)
        self.assertIsInstance(FakeInlet.last_max_buffered, int)
        self.assertFalse(worker.is_alive)

    def test_float_max_buffered_is_rejected_before_worker_start(self) -> None:
        with self.assertRaises(TypeError):
            AcquisitionConfig(max_buffered_seconds=360.0).validate()  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
