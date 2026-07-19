"""Threaded discovery and acquisition services."""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import replace
from typing import Any

from mne_lsl.lsl import StreamInlet, local_clock, resolve_streams

from lsl_gui.models import AcquisitionConfig, DataChunk, StreamDescriptor, StreamState

LOGGER = logging.getLogger(__name__)
EventSink = Callable[[str, str, object], None]

DEMO_BUNDLE_SOURCE_ID = "demo-bundle-source"
DEMO_VIEWS = (
    ("Demo-EEG", "EEG", ("Fz", "C3", "C4", "Pz"), (0, 1, 2, 3)),
    ("Demo-Aux", "Sensors", ("Respiration", "Temperature"), (4, 5)),
    ("Demo-Events", "Markers", ("EventCode",), (6,)),
)


def _descriptors_for_sinfo(sinfo: Any) -> list[StreamDescriptor]:
    descriptor = StreamDescriptor.from_sinfo(sinfo)
    if descriptor.source_id != DEMO_BUNDLE_SOURCE_ID:
        return [descriptor]
    return [
        StreamDescriptor(
            key=f"{descriptor.key}:{name}",
            name=name,
            stype=stype,
            source_id=f"{descriptor.source_id}:{name}",
            hostname=descriptor.hostname,
            n_channels=len(channel_names),
            sfreq=descriptor.sfreq,
            channel_names=channel_names,
            dtype=descriptor.dtype,
            channel_indices=channel_indices,
        )
        for name, stype, channel_names, channel_indices in DEMO_VIEWS
    ]


def discover_streams(timeout: float = 1.0) -> list[tuple[StreamDescriptor, Any]]:
    """Discover all visible streams and return descriptors with their StreamInfo."""

    unique: dict[str, tuple[StreamDescriptor, Any]] = {}
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        streams = resolve_streams(timeout=min(0.5, remaining))
        for sinfo in streams:
            for descriptor in _descriptors_for_sinfo(sinfo):
                unique[descriptor.key] = (descriptor, sinfo)
    return list(unique.values())


class StreamWorker:
    """Own a single inlet and pull its data outside the GUI thread."""

    def __init__(
        self,
        descriptor: StreamDescriptor,
        sinfo: Any,
        config: AcquisitionConfig,
        event_sink: EventSink,
        inlet_factory: Callable[..., Any] = StreamInlet,
    ) -> None:
        self.descriptor = descriptor
        self._sinfo = sinfo
        self._config = config
        self._event_sink = event_sink
        self._inlet_factory = inlet_factory
        self._stop_event = threading.Event()
        self._read_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._recorder: Any | None = None
        self._recorder_lock = threading.Lock()
        self.state = StreamState.DISCONNECTED

    @property
    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def connect(self) -> None:
        if self.is_alive:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"lsl-{self.descriptor.name}",
            daemon=True,
        )
        self._thread.start()

    def start_reading(self, recorder: Any) -> None:
        if not self.is_alive or self.state != StreamState.CONNECTED:
            raise RuntimeError(f"{self.descriptor.name} is not connected")
        with self._recorder_lock:
            self._recorder = recorder
        self._read_event.set()
        self._set_state(StreamState.READING)

    def stop_reading(self) -> None:
        self._read_event.clear()
        with self._recorder_lock:
            self._recorder = None
        if self.is_alive and self.state == StreamState.READING:
            self._set_state(StreamState.CONNECTED)

    def disconnect(self, timeout: float = 3.0) -> None:
        self.stop_reading()
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                raise TimeoutError(f"Could not disconnect {self.descriptor.name}")

    def _emit(self, event: str, payload: object) -> None:
        self._event_sink(self.descriptor.key, event, payload)

    def _set_state(self, state: StreamState) -> None:
        self.state = state
        self._emit("state", state)

    def _run(self) -> None:
        inlet: Any | None = None
        failed = False
        self._set_state(StreamState.CONNECTING)
        try:
            inlet = self._inlet_factory(
                self._sinfo,
                max_buffered=self._config.max_buffered_seconds,
            )
            inlet.open_stream(timeout=2.0)
            details = StreamDescriptor.from_sinfo(inlet.get_sinfo(timeout=1.0))
            if self.descriptor.source_id.startswith(DEMO_BUNDLE_SOURCE_ID):
                details = self.descriptor
            self.descriptor = replace(details, key=self.descriptor.key)
            self._emit("descriptor", self.descriptor)
            correction = float(inlet.time_correction(timeout=1.0))
            wall_offset = time.time() - local_clock()
            last_correction_update = time.monotonic()
            self._set_state(StreamState.CONNECTED)
            while not self._stop_event.is_set():
                if not self._read_event.wait(timeout=0.05):
                    continue
                samples, timestamps = inlet.pull_chunk(
                    timeout=self._config.pull_timeout,
                    max_samples=self._config.max_samples,
                )
                if len(timestamps) == 0:
                    continue
                if time.monotonic() - last_correction_update >= 5.0:
                    correction = float(inlet.time_correction(timeout=0.2))
                    last_correction_update = time.monotonic()
                row_count = min(len(samples), len(timestamps))
                remote = tuple(float(value) for value in timestamps[:row_count])
                corrected = tuple(value + correction for value in remote)
                host = tuple(value + wall_offset for value in corrected)
                indices = self.descriptor.channel_indices or tuple(
                    range(self.descriptor.n_channels)
                )
                selected_samples = tuple(
                    tuple(row[index] for index in indices)
                    for row in samples[:row_count]
                )
                chunk = DataChunk(
                    stream_key=self.descriptor.key,
                    samples=selected_samples,
                    remote_timestamps=remote,
                    corrected_timestamps=corrected,
                    host_timestamps=host,
                )
                with self._recorder_lock:
                    if self._recorder is not None:
                        self._recorder.append(chunk)
                self._emit("chunk", chunk)
        except Exception as exc:  # Worker must report all hardware/runtime failures.
            failed = True
            LOGGER.exception("LSL worker failed for %s", self.descriptor.name)
            self._emit("error", str(exc))
            self._set_state(StreamState.ERROR)
        finally:
            if inlet is not None:
                try:
                    inlet.close_stream()
                except Exception:
                    LOGGER.exception("Failed to close %s", self.descriptor.name)
            if not failed:
                self._set_state(StreamState.DISCONNECTED)


class AcquisitionController:
    """Coordinate selected workers and expose an event queue to the GUI."""

    def __init__(self, config: AcquisitionConfig) -> None:
        config.validate()
        self.config = config
        self.events: queue.Queue[tuple[str, str, object]] = queue.Queue()
        self.plot_events: queue.Queue[tuple[str, str, object]] = queue.Queue(maxsize=256)
        self.workers: dict[str, StreamWorker] = {}
        self.descriptors: dict[str, StreamDescriptor] = {}
        self._lock = threading.RLock()

    def add_stream(self, descriptor: StreamDescriptor, sinfo: Any) -> None:
        with self._lock:
            if descriptor.key in self.workers:
                return
            self.descriptors[descriptor.key] = descriptor
            self.workers[descriptor.key] = StreamWorker(
                descriptor, sinfo, self.config, self._emit
            )

    def _emit(self, key: str, event: str, payload: object) -> None:
        if event == "descriptor" and isinstance(payload, StreamDescriptor):
            with self._lock:
                self.descriptors[key] = payload
        item = (key, event, payload)
        if event != "chunk":
            self.events.put(item)
            return
        try:
            self.plot_events.put_nowait(item)
        except queue.Full:
            # Plot updates are best effort; recording happens before this queue.
            return

    def connect_all(self) -> None:
        with self._lock:
            workers = tuple(self.workers.values())
        for worker in workers:
            worker.connect()

    def connect_stream(self, key: str) -> None:
        """Connect one previously added stream."""

        with self._lock:
            worker = self.workers.get(key)
        if worker is None:
            raise KeyError(f"Unknown stream: {key}")
        worker.connect()

    def disconnect_stream(self, key: str) -> None:
        """Disconnect and remove one stream without affecting the others."""

        with self._lock:
            worker = self.workers.get(key)
        if worker is None:
            return
        worker.disconnect()
        if worker.is_alive:
            raise TimeoutError(f"Could not disconnect {worker.descriptor.name}")
        with self._lock:
            self.workers.pop(key, None)
            self.descriptors.pop(key, None)

    def connected_keys(self) -> tuple[str, ...]:
        """Return the keys of streams ready to record."""

        with self._lock:
            items = tuple(self.workers.items())
        return tuple(
            key for key, worker in items
            if worker.is_alive and worker.state == StreamState.CONNECTED
        )

    def start_all(self, recorder: Any) -> None:
        with self._lock:
            workers = tuple(self.workers.values())
        active = [
            worker
            for worker in workers
            if worker.is_alive and worker.state == StreamState.CONNECTED
        ]
        if not active:
            raise RuntimeError("No connected streams are available")
        for worker in active:
            recorder.register_stream(worker.descriptor)
        started: list[StreamWorker] = []
        try:
            for worker in active:
                worker.start_reading(recorder)
                started.append(worker)
        except Exception:
            for worker in started:
                worker.stop_reading()
            raise

    def stop_all(self) -> None:
        with self._lock:
            workers = tuple(self.workers.values())
        for worker in workers:
            worker.stop_reading()

    def disconnect_all(self) -> None:
        errors: list[str] = []
        with self._lock:
            workers = tuple(self.workers.values())
        for worker in workers:
            try:
                worker.disconnect()
            except TimeoutError as exc:
                errors.append(str(exc))
        with self._lock:
            self.workers.clear()
            self.descriptors.clear()
        if errors:
            raise TimeoutError("; ".join(errors))
