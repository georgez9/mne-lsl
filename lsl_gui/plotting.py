"""Reusable three-slot waveform dashboard and headless plotting helpers."""

from __future__ import annotations

import math
import tkinter as tk
from collections import deque
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from lsl_gui.models import StreamDescriptor

PlotRows = deque[tuple[float, tuple[object, ...]]]
PlotTarget = tuple[str, int]


def build_plot_targets(
    descriptors: dict[str, StreamDescriptor],
) -> dict[str, PlotTarget]:
    """Build unique display labels without losing duplicate channel names."""

    targets: dict[str, PlotTarget] = {}
    for key, descriptor in descriptors.items():
        identity = descriptor.source_id or key[-8:]
        for channel_index, channel_name in enumerate(descriptor.channel_names):
            base = (
                f"{descriptor.name} [{identity}] / "
                f"{channel_index + 1}: {channel_name}"
            )
            label = base
            suffix = 2
            while label in targets:
                label = f"{base} ({suffix})"
                suffix += 1
            targets[label] = (key, channel_index)
    return targets


def channel_series(
    rows: PlotRows,
    channel_index: int,
) -> tuple[list[float], list[float]]:
    """Extract finite relative timestamps and values for one channel."""

    if not rows:
        return [], []
    start = rows[0][0]
    times: list[float] = []
    values: list[float] = []
    for timestamp, sample in rows:
        try:
            value = float(sample[channel_index])
        except (IndexError, TypeError, ValueError):
            continue
        if math.isfinite(value):
            times.append(timestamp - start)
            values.append(value)
    return times, values


def automatic_y_limits(values: list[float]) -> tuple[float, float]:
    """Compute padded Y limits for the currently visible finite values."""

    finite = [value for value in values if math.isfinite(value)]
    if not finite:
        return -1.0, 1.0
    low = min(finite)
    high = max(finite)
    span = high - low
    if span == 0:
        padding = max(abs(low) * 0.05, 1e-6)
    else:
        padding = span * 0.08
    return low - padding, high + padding


class WaveformDashboard:
    """Three independent single-channel plots with per-slot selectors."""

    def __init__(self, parent: ttk.Frame) -> None:
        self.variables: list[tk.StringVar] = []
        self.combos: list[ttk.Combobox] = []
        self.axes = []
        self.canvases: list[FigureCanvasTkAgg] = []
        self.targets: dict[str, PlotTarget] = {}
        for index in range(3):
            panel = ttk.LabelFrame(parent, text=f"Waveform {index + 1}", padding=4)
            panel.pack(fill=tk.BOTH, expand=True, pady=(0, 4))
            variable = tk.StringVar()
            combo = ttk.Combobox(panel, textvariable=variable, state="readonly")
            combo.pack(fill=tk.X, pady=(0, 3))
            figure = Figure(figsize=(7, 1.65), dpi=100)
            axes = figure.add_subplot(111)
            canvas = FigureCanvasTkAgg(figure, master=panel)
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            self.variables.append(variable)
            self.combos.append(combo)
            self.axes.append(axes)
            self.canvases.append(canvas)

    def update_options(self, descriptors: dict[str, StreamDescriptor]) -> None:
        """Refresh stream/channel options while retaining valid selections."""

        targets = build_plot_targets(descriptors)
        self.targets = targets
        labels = list(targets)
        for index, (variable, combo) in enumerate(zip(self.variables, self.combos, strict=True)):
            combo["values"] = labels
            if variable.get() not in targets:
                variable.set(labels[index % len(labels)] if labels else "")

    def refresh(
        self,
        plot_data: dict[str, PlotRows],
        descriptors: dict[str, StreamDescriptor],
    ) -> None:
        """Redraw each slot from its selected stream and channel."""

        snapshots: dict[str, PlotRows] = {
            key: deque(rows) for key, rows in plot_data.items()
        }
        for variable, axes, canvas in zip(
            self.variables, self.axes, self.canvases, strict=True
        ):
            axes.clear()
            target = self.targets.get(variable.get())
            if target is not None:
                key, channel_index = target
                descriptor = descriptors.get(key)
                rows = snapshots.get(key, deque())
                times, values = channel_series(rows, channel_index)
                if values and descriptor is not None:
                    axes.plot(times, values, linewidth=0.9, color="#2563eb")
                    axes.set_ylabel(descriptor.channel_names[channel_index], fontsize=8)
                    axes.set_ylim(*automatic_y_limits(values))
            axes.set_xlabel("Time (s)", fontsize=8)
            axes.grid(True, alpha=0.25)
            axes.tick_params(labelsize=7)
            canvas.draw_idle()
