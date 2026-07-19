"""Tkinter user interface for the multi-stream LSL recorder."""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from collections import deque
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from lsl_gui.acquisition import AcquisitionController, discover_streams
from lsl_gui.models import AcquisitionConfig, DataChunk, StreamDescriptor, StreamState
from lsl_gui.plotting import WaveformDashboard
from lsl_gui.recording import SessionRecorder
from lsl_gui.runtime import configure_logging, default_recording_directory

LOGGER = logging.getLogger(__name__)


class LslRecorderApp:
    """Small desktop UI for discovery, recording, plotting, and saving."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("LSL Multi-stream Recorder")
        self.root.geometry("1280x900")
        self.controller = AcquisitionController(AcquisitionConfig())
        self.discovery_results: queue.Queue[
            tuple[int, list[tuple[StreamDescriptor, Any]], str | None]
        ] = queue.Queue()
        self.discovery_generation = 0
        self.is_discovering = False
        self.disconnect_results: queue.Queue[tuple[str, str | None]] = queue.Queue()
        self.disconnect_threads: set[threading.Thread] = set()
        self.discovered: dict[str, tuple[StreamDescriptor, Any]] = {}
        self.states: dict[str, StreamState] = {}
        self.plot_data: dict[str, deque[tuple[float, tuple[object, ...]]]] = {}
        self.recorder: SessionRecorder | None = None
        self.is_recording = False
        self.output_var = tk.StringVar(value=str(default_recording_directory()))
        self.participant_var = tk.StringVar(value="P01")
        self.session_var = tk.StringVar(value="session1")
        self.max_samples_var = tk.StringVar(value="256")
        self.pull_timeout_var = tk.StringVar(value="0.1")
        self.plot_window_var = tk.StringVar(value="10")
        self.status_var = tk.StringVar(value="Ready - click Discover streams")
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(50, self._process_events)
        self.root.after(50, self._process_discovery_result)
        self.root.after(50, self._process_disconnect_results)
        self.root.after(100, self._refresh_plot)

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self.root, padding=8)
        toolbar.pack(fill=tk.X)
        self.discover_button = ttk.Button(toolbar, text="1. Discover", command=self._discover)
        self.start_button = ttk.Button(toolbar, text="2. Start reading", command=self._start)
        self.stop_button = ttk.Button(toolbar, text="3. Stop reading", command=self._stop)
        self.save_button = ttk.Button(toolbar, text="4. Save", command=self._save)
        for widget in (
            self.discover_button,
            self.start_button,
            self.stop_button,
            self.save_button,
        ):
            widget.pack(side=tk.LEFT, padx=3)
        ttk.Label(
            toolbar,
            text="Check a stream row to connect; uncheck it to disconnect.",
        ).pack(side=tk.LEFT, padx=12)

        settings = ttk.LabelFrame(self.root, text="Recording parameters", padding=8)
        settings.pack(fill=tk.X, padx=8)
        ttk.Label(settings, text="Participant").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(settings, textvariable=self.participant_var, width=14).grid(row=0, column=1, padx=5)
        ttk.Label(settings, text="Session").grid(row=0, column=2, sticky=tk.W)
        ttk.Entry(settings, textvariable=self.session_var, width=18).grid(row=0, column=3, padx=5)
        ttk.Label(settings, text="Output directory").grid(row=0, column=4, sticky=tk.W)
        ttk.Entry(settings, textvariable=self.output_var).grid(row=0, column=5, padx=5, sticky=tk.EW)
        ttk.Button(settings, text="Browse", command=self._choose_output).grid(row=0, column=6)
        ttk.Label(settings, text="Chunk samples").grid(row=1, column=0, sticky=tk.W, pady=(7, 0))
        ttk.Entry(settings, textvariable=self.max_samples_var, width=14).grid(row=1, column=1, padx=5, pady=(7, 0))
        ttk.Label(settings, text="Pull timeout (s)").grid(row=1, column=2, sticky=tk.W, pady=(7, 0))
        ttk.Entry(settings, textvariable=self.pull_timeout_var, width=18).grid(row=1, column=3, padx=5, pady=(7, 0))
        ttk.Label(settings, text="Plot window (s)").grid(row=1, column=4, sticky=tk.W, pady=(7, 0))
        ttk.Entry(settings, textvariable=self.plot_window_var, width=12).grid(row=1, column=5, sticky=tk.W, padx=5, pady=(7, 0))
        settings.columnconfigure(5, weight=1)

        paned = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        streams_frame = ttk.LabelFrame(paned, text="Available streams", padding=5)
        plot_frame = ttk.LabelFrame(paned, text="Live waveforms", padding=5)
        paned.add(streams_frame, weight=2)
        paned.add(plot_frame, weight=3)

        columns = ("connected", "name", "type", "source", "channels", "rate", "state")
        self.stream_table = ttk.Treeview(streams_frame, columns=columns, show="headings", selectmode="none")
        widths = (70, 150, 90, 145, 65, 70, 95)
        for column, width in zip(columns, widths, strict=True):
            self.stream_table.heading(column, text=column.title())
            self.stream_table.column(column, width=width, anchor=tk.W)
        scrollbar = ttk.Scrollbar(streams_frame, orient=tk.VERTICAL, command=self.stream_table.yview)
        self.stream_table.configure(yscrollcommand=scrollbar.set)
        self.stream_table.bind("<Button-1>", self._on_stream_table_click)
        self.stream_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.waveforms = WaveformDashboard(plot_frame)

        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X)
        self._update_buttons()

    def _choose_output(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.output_var.get())
        if chosen:
            self.output_var.set(chosen)

    def _discover(self) -> None:
        if self.controller.workers:
            messagebox.showwarning("Streams connected", "Disconnect before discovering again.")
            return
        if self.is_discovering:
            return
        self.is_discovering = True
        self.discovery_generation += 1
        generation = self.discovery_generation
        self.status_var.set("Discovering LSL streams...")
        self.discover_button.configure(state=tk.DISABLED)
        self._update_buttons()
        threading.Thread(target=self._discover_worker, args=(generation,), daemon=True).start()

    def _discover_worker(self, generation: int) -> None:
        try:
            result = discover_streams(timeout=1.5)
            self.discovery_results.put((generation, result, None))
        except Exception as exc:
            self.discovery_results.put((generation, [], str(exc)))

    def _process_discovery_result(self) -> None:
        try:
            generation, streams, error = self.discovery_results.get_nowait()
        except queue.Empty:
            pass
        else:
            if generation == self.discovery_generation and not self.controller.workers:
                self._show_discovered(streams, error)
            self.is_discovering = False
            self._update_buttons()
        self.root.after(50, self._process_discovery_result)

    def _show_discovered(self, streams: list[tuple[StreamDescriptor, Any]], error: str | None) -> None:
        if error:
            self.status_var.set(f"Discovery failed: {error}")
            return
        self.discovered = {descriptor.key: (descriptor, sinfo) for descriptor, sinfo in streams}
        self.stream_table.delete(*self.stream_table.get_children())
        for descriptor, _ in streams:
            self.stream_table.insert(
                "",
                tk.END,
                iid=descriptor.key,
                values=(
                    "☐",
                    descriptor.name,
                    descriptor.stype,
                    descriptor.source_id,
                    descriptor.n_channels,
                    f"{descriptor.sfreq:g}",
                    StreamState.DISCONNECTED.value,
                ),
            )
        self.waveforms.update_options(
            {key: descriptor for key, (descriptor, _) in self.discovered.items()}
        )
        self.status_var.set(f"Found {len(streams)} stream(s)")
        self._update_buttons()

    def _read_acquisition_config(self) -> AcquisitionConfig | None:
        try:
            config = AcquisitionConfig(
                max_samples=int(self.max_samples_var.get()),
                pull_timeout=float(self.pull_timeout_var.get()),
                plot_window_seconds=float(self.plot_window_var.get()),
            )
            config.validate()
        except (TypeError, ValueError) as exc:
            messagebox.showerror("Invalid parameters", str(exc))
            return None
        return config

    def _on_stream_table_click(self, event: tk.Event[tk.Misc]) -> str | None:
        if self.stream_table.identify_column(event.x) != "#1":
            return None
        key = self.stream_table.identify_row(event.y)
        if not key:
            return "break"
        if self.is_recording:
            messagebox.showwarning(
                "Recording in progress",
                "Stop reading before connecting or disconnecting streams.",
            )
            return "break"
        state = self.states.get(key, StreamState.DISCONNECTED)
        if state in {StreamState.CONNECTING, StreamState.DISCONNECTING}:
            return "break"
        if state in {StreamState.CONNECTED, StreamState.READING}:
            self._request_disconnect(key)
        else:
            self._request_connect(key)
        return "break"

    def _request_connect(self, key: str) -> None:
        if not self.controller.workers:
            config = self._read_acquisition_config()
            if config is None:
                return
            self.controller = AcquisitionController(config)
        descriptor, sinfo = self.discovered[key]
        self.controller.add_stream(descriptor, sinfo)
        self.states[key] = StreamState.CONNECTING
        self.plot_data.setdefault(key, deque())
        self._set_row_connection(key, "☑", StreamState.CONNECTING)
        self.controller.connect_stream(key)
        self.status_var.set(f"Connecting {descriptor.name}...")
        self._update_buttons()

    def _request_disconnect(self, key: str) -> None:
        self.states[key] = StreamState.DISCONNECTING
        self._set_row_connection(key, "☑", StreamState.DISCONNECTING)
        thread = threading.Thread(
            target=self._disconnect_stream_worker,
            args=(key,),
            daemon=True,
        )
        self.disconnect_threads.add(thread)
        thread.start()

    def _disconnect_stream_worker(self, key: str) -> None:
        try:
            self.controller.disconnect_stream(key)
        except (KeyError, TimeoutError) as exc:
            self.disconnect_results.put((key, str(exc)))
        else:
            self.disconnect_results.put((key, None))

    def _process_disconnect_results(self) -> None:
        while True:
            try:
                key, error = self.disconnect_results.get_nowait()
            except queue.Empty:
                break
            if error:
                self.states[key] = StreamState.ERROR
                self._set_row_connection(key, "☐", StreamState.ERROR)
                self.status_var.set(error)
            else:
                self.states.pop(key, None)
                self.plot_data.pop(key, None)
                self._set_row_connection(key, "☐", StreamState.DISCONNECTED)
                name = self.discovered[key][0].name
                self.status_var.set(f"Disconnected {name}")
        self.disconnect_threads = {
            thread for thread in self.disconnect_threads if thread.is_alive()
        }
        self._update_buttons()
        self.root.after(50, self._process_disconnect_results)

    def _set_row_connection(
        self,
        key: str,
        checked: str,
        state: StreamState,
    ) -> None:
        if not self.stream_table.exists(key):
            return
        values = list(self.stream_table.item(key, "values"))
        values[0] = checked
        values[-1] = state.value
        self.stream_table.item(key, values=values)

    def _update_stream_metadata_row(
        self,
        key: str,
        descriptor: StreamDescriptor,
    ) -> None:
        if not self.stream_table.exists(key):
            return
        values = list(self.stream_table.item(key, "values"))
        values[1:6] = [
            descriptor.name,
            descriptor.stype,
            descriptor.source_id,
            descriptor.n_channels,
            f"{descriptor.sfreq:g}",
        ]
        self.stream_table.item(key, values=values)

    def _start(self) -> None:
        if not self.controller.workers:
            return
        try:
            recorder = SessionRecorder(
                Path(self.output_var.get()),
                self.participant_var.get(),
                self.session_var.get(),
            )
            self.recorder = recorder
            self.controller.start_all(recorder)
        except (OSError, RuntimeError, ValueError) as exc:
            if self.recorder is not None:
                self.recorder.discard()
                self.recorder = None
            messagebox.showerror("Cannot start", str(exc))
            return
        self.is_recording = True
        self.status_var.set("Reading and recording data...")
        self._update_buttons()

    def _stop(self) -> None:
        self.controller.stop_all()
        if self.recorder is not None:
            self.recorder.close()
        self.is_recording = False
        self.status_var.set("Reading stopped. Click Save to finalize the session.")
        self._update_buttons()

    def _save(self) -> None:
        if self.recorder is None or self.is_recording:
            return
        try:
            path = self.recorder.save()
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc))
            return
        self.recorder = None
        self.status_var.set(f"Saved: {path}")
        messagebox.showinfo("Saved", f"Session saved to:\n{path}")
        self._update_buttons()

    def _process_events(self) -> None:
        pending_events: list[tuple[str, str, object]] = []
        for source in (self.controller.events, self.controller.plot_events):
            while True:
                try:
                    pending_events.append(source.get_nowait())
                except queue.Empty:
                    break
        for key, event, payload in pending_events:
            if event == "state":
                if (
                    payload == StreamState.DISCONNECTED
                    and self.states.get(key) == StreamState.DISCONNECTING
                ):
                    continue
                self.states[key] = payload  # type: ignore[assignment]
                checked = "☐" if payload in {StreamState.DISCONNECTED, StreamState.ERROR} else "☑"
                self._set_row_connection(key, checked, payload)  # type: ignore[arg-type]
            elif event == "descriptor":
                old = self.discovered.get(key)
                if old is not None:
                    self.discovered[key] = (payload, old[1])  # type: ignore[assignment]
                    self._update_stream_metadata_row(key, payload)  # type: ignore[arg-type]
                    self.waveforms.update_options(
                        {
                            stream_key: descriptor
                            for stream_key, (descriptor, _) in self.discovered.items()
                        }
                    )
            elif event == "chunk":
                self._accept_chunk(payload)  # type: ignore[arg-type]
            elif event == "error":
                descriptor = self.controller.descriptors.get(key)
                name = descriptor.name if descriptor is not None else key
                self.status_var.set(f"{name}: {payload}")
        self._update_buttons()
        self.root.after(50, self._process_events)

    def _accept_chunk(self, chunk: DataChunk) -> None:
        buffer = self.plot_data.setdefault(chunk.stream_key, deque())
        for timestamp, sample in zip(chunk.corrected_timestamps, chunk.samples, strict=False):
            buffer.append((timestamp, sample))
        cutoff = chunk.corrected_timestamps[-1] - self.controller.config.plot_window_seconds
        while buffer and buffer[0][0] < cutoff:
            buffer.popleft()

    def _refresh_plot(self) -> None:
        descriptors = {
            key: descriptor for key, (descriptor, _) in self.discovered.items()
        }
        self.waveforms.refresh(self.plot_data, descriptors)
        self.root.after(200, self._refresh_plot)

    def _update_buttons(self) -> None:
        connected = bool(self.controller.connected_keys())
        transitioning = any(
            state in {StreamState.CONNECTING, StreamState.DISCONNECTING}
            for state in self.states.values()
        )
        can_discover = not self.controller.workers and not self.is_discovering
        self.discover_button.configure(state=tk.NORMAL if can_discover else tk.DISABLED)
        self.start_button.configure(state=tk.NORMAL if connected and not transitioning and not self.is_recording and self.recorder is None else tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL if self.is_recording else tk.DISABLED)
        self.save_button.configure(state=tk.NORMAL if self.recorder is not None and not self.is_recording else tk.DISABLED)

    def _on_close(self) -> None:
        if self.is_recording and not messagebox.askyesno("Recording", "Stop recording and close the application?"):
            return
        if self.is_recording:
            self._stop()
        if self.recorder is not None and not messagebox.askyesno(
            "Unsaved data", "Close while keeping pending recording files for recovery?"
        ):
            return
        for thread in tuple(self.disconnect_threads):
            thread.join(timeout=3.5)
        try:
            self.controller.disconnect_all()
        except TimeoutError:
            LOGGER.exception("A stream did not disconnect cleanly")
        self.root.destroy()


def run() -> None:
    """Start the application."""

    configure_logging()
    root = tk.Tk()
    LslRecorderApp(root)
    root.mainloop()
