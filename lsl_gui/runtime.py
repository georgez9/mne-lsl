"""Runtime paths and logging suitable for source and frozen applications."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """Return whether the application is running from a PyInstaller bundle."""

    return bool(getattr(sys, "frozen", False))


def user_data_root() -> Path:
    """Return a writable, user-visible root for packaged application data."""

    if is_frozen():
        return Path.home() / "Documents" / "LSL Recorder"
    return Path.cwd()


def default_recording_directory() -> Path:
    """Return the default recording output directory."""

    configured = os.environ.get("LSL_RECORDER_DATA_DIR")
    if configured:
        return Path(configured).expanduser()
    return user_data_root() / "Data"


def configure_logging() -> None:
    """Configure console logging in development and file logging when frozen."""

    handlers: list[logging.Handler] = []
    if is_frozen():
        log_dir = user_data_root() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(
            logging.FileHandler(log_dir / "lsl_recorder.log", encoding="utf-8")
        )
    else:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )
