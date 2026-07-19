"""Entry point used by the frozen Windows application."""

from __future__ import annotations

import sys

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from mne_lsl.lsl import library_version

from lsl_gui.gui import run
from lsl_gui.runtime import default_recording_directory


def main() -> None:
    """Start the GUI or verify that packaged runtime imports are available."""

    if "--smoke-test" in sys.argv:
        import tkinter as tk

        if library_version() <= 0:
            raise RuntimeError("liblsl did not report a valid version")
        default_recording_directory().mkdir(parents=True, exist_ok=True)
        root = tk.Tk()
        root.withdraw()
        FigureCanvasTkAgg(Figure(figsize=(1, 1)), master=root)
        root.update_idletasks()
        root.destroy()
        return
    run()


if __name__ == "__main__":
    main()
