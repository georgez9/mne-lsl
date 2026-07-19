"""Crash-resilient per-stream CSV recording."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO
from uuid import uuid4

from lsl_gui.models import DataChunk, StreamDescriptor


def sanitize_name(value: str, fallback: str = "stream") -> str:
    """Return a Windows-safe file name component."""

    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("._")
    return cleaned or fallback


class SessionRecorder:
    """Append chunks to temporary CSV files and atomically finalize a session."""

    def __init__(self, output_root: Path, participant: str, session: str) -> None:
        self.output_root = output_root.resolve()
        self.participant = sanitize_name(participant, "participant")
        self.session = sanitize_name(session, "session")
        self.started_at = datetime.now(timezone.utc)
        stamp = self.started_at.strftime("%Y%m%dT%H%M%S_%fZ")
        self.session_name = f"{self.participant}_{self.session}_{stamp}"
        self.pending_dir = self.output_root / f".{self.session_name}_{uuid4().hex[:8]}.pending"
        self.pending_dir.mkdir(parents=True, exist_ok=False)
        self._files: dict[str, TextIO] = {}
        self._writers: dict[str, csv.writer] = {}
        self._paths: dict[str, Path] = {}
        self._descriptors: dict[str, StreamDescriptor] = {}
        self._counts: dict[str, int] = {}
        self._lock = threading.Lock()
        self._closed = False

    def register_stream(self, descriptor: StreamDescriptor) -> None:
        with self._lock:
            if self._closed:
                raise RuntimeError("recording is already closed")
            suffix = hashlib.sha256(descriptor.key.encode("utf-8")).hexdigest()[:12]
            filename = f"{sanitize_name(descriptor.name)}_{suffix}.csv.part"
            path = self.pending_dir / filename
            counter = 2
            while path in self._paths.values() or path.exists():
                path = self.pending_dir / f"{sanitize_name(descriptor.name)}_{suffix}_{counter}.csv.part"
                counter += 1
            handle = path.open("w", newline="", encoding="utf-8")
            writer = csv.writer(handle)
            writer.writerow(
                ["time_host_utc", "time_lsl_corrected", "time_lsl_remote", *descriptor.channel_names]
            )
            self._files[descriptor.key] = handle
            self._writers[descriptor.key] = writer
            self._paths[descriptor.key] = path
            self._descriptors[descriptor.key] = descriptor
            self._counts[descriptor.key] = 0

    def append(self, chunk: DataChunk) -> None:
        with self._lock:
            if self._closed or chunk.stream_key not in self._writers:
                return
            writer = self._writers[chunk.stream_key]
            row_count = min(
                len(chunk.samples),
                len(chunk.remote_timestamps),
                len(chunk.corrected_timestamps),
                len(chunk.host_timestamps),
            )
            expected = self._descriptors[chunk.stream_key].n_channels
            written = 0
            for index in range(row_count):
                sample = chunk.samples[index]
                if len(sample) != expected:
                    continue
                host_iso = datetime.fromtimestamp(
                    chunk.host_timestamps[index], tz=timezone.utc
                ).isoformat()
                writer.writerow(
                    [
                        host_iso,
                        chunk.corrected_timestamps[index],
                        chunk.remote_timestamps[index],
                        *sample,
                    ]
                )
                written += 1
            self._counts[chunk.stream_key] += written

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            for handle in self._files.values():
                handle.flush()
                handle.close()
            self._closed = True

    def save(self) -> Path:
        self.close()
        final_dir = self.output_root / self.participant / self.session_name
        final_dir.parent.mkdir(parents=True, exist_ok=True)
        if final_dir.exists():
            raise FileExistsError(f"session directory already exists: {final_dir}")
        for path in self._paths.values():
            path.replace(path.with_suffix(""))
        manifest = {
            "participant": self.participant,
            "session": self.session,
            "started_at_utc": self.started_at.isoformat(),
            "saved_at_utc": datetime.now(timezone.utc).isoformat(),
            "streams": [
                {
                    **descriptor.as_dict(),
                    "samples_written": self._counts[key],
                    "file": self._paths[key].with_suffix("").name,
                }
                for key, descriptor in self._descriptors.items()
            ],
        }
        manifest_tmp = self.pending_dir / "session.json.tmp"
        manifest_tmp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        manifest_tmp.replace(self.pending_dir / "session.json")
        self.pending_dir.replace(final_dir)
        return final_dir

    def discard(self) -> None:
        self.close()
        if self.pending_dir.exists():
            shutil.rmtree(self.pending_dir)
