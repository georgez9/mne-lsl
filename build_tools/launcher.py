"""Entry point used by the frozen Windows application."""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path


def _write_smoke_report(message: str) -> None:
    """Write a diagnostic report when the build requests one."""

    report_path = os.environ.get("LSL_RECORDER_SMOKE_REPORT")
    if report_path:
        Path(report_path).write_text(message, encoding="utf-8")


def _smoke_test() -> None:
    """Load native and GUI dependencies without entering the main loop."""

    _write_smoke_report("START\n")
    import tkinter as tk

    _write_smoke_report("TK_IMPORTED\n")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure

    _write_smoke_report("MATPLOTLIB_IMPORTED\n")
    from mne_lsl.lsl import library_version

    _write_smoke_report("MNE_LSL_IMPORTED\n")
    from lsl_gui.runtime import default_recording_directory

    if library_version() <= 0:
        raise RuntimeError("liblsl did not report a valid version")
    _write_smoke_report("LIBLSL_LOADED\n")
    default_recording_directory().mkdir(parents=True, exist_ok=True)
    root = tk.Tk()
    try:
        root.withdraw()
        _write_smoke_report("TK_CREATED\n")
        FigureCanvasTkAgg(Figure(figsize=(1, 1)), master=root)
        root.update_idletasks()
        _write_smoke_report("CANVAS_CREATED\n")
    finally:
        root.destroy()


def main() -> int:
    """Start the GUI or return a verifiable packaged-runtime status code."""

    if "--smoke-test" in sys.argv:
        try:
            _smoke_test()
        except Exception:  # Capture native import failures for release diagnostics.
            _write_smoke_report(traceback.format_exc())
            return 1
        _write_smoke_report("OK\n")
        return 0

    from lsl_gui.gui import run

    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
