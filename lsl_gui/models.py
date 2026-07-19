"""Domain models shared by the GUI and acquisition services."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class StreamState(str, Enum):
    """Lifecycle of one selected LSL stream."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    READING = "reading"
    DISCONNECTING = "disconnecting"
    ERROR = "error"


@dataclass(frozen=True)
class StreamDescriptor:
    """Serializable snapshot of an LSL StreamInfo object."""

    key: str
    name: str
    stype: str
    source_id: str
    hostname: str
    n_channels: int
    sfreq: float
    channel_names: tuple[str, ...]
    dtype: str
    channel_indices: tuple[int, ...] = ()

    @classmethod
    def from_sinfo(cls, sinfo: Any) -> "StreamDescriptor":
        names = tuple(sinfo.get_channel_names() or ())
        n_channels = int(sinfo.n_channels)
        if len(names) != n_channels:
            names = tuple(f"ch_{index + 1:03d}" for index in range(n_channels))
        uid = str(sinfo.uid or "")
        source_id = str(sinfo.source_id or "")
        key = uid or source_id or f"{sinfo.name}|{sinfo.stype}|{sinfo.hostname}"
        return cls(
            key=key,
            name=str(sinfo.name),
            stype=str(sinfo.stype),
            source_id=source_id,
            hostname=str(sinfo.hostname),
            n_channels=n_channels,
            sfreq=float(sinfo.sfreq),
            channel_names=names,
            dtype=str(sinfo.dtype),
            channel_indices=tuple(range(n_channels)),
        )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AcquisitionConfig:
    """Parameters controlling inlet reads and plotting."""

    max_samples: int = 256
    pull_timeout: float = 0.1
    max_buffered_seconds: int = 360
    plot_window_seconds: float = 10.0
    max_plot_channels: int = 8

    def validate(self) -> None:
        if self.max_samples <= 0:
            raise ValueError("max_samples must be greater than zero")
        if not 0 < self.pull_timeout <= 2:
            raise ValueError("pull_timeout must be between 0 and 2 seconds")
        if isinstance(self.max_buffered_seconds, bool) or not isinstance(
            self.max_buffered_seconds, int
        ):
            raise TypeError("max_buffered_seconds must be an integer")
        if self.max_buffered_seconds <= 0 or self.plot_window_seconds <= 0:
            raise ValueError("buffer and plot windows must be greater than zero")
        if self.max_plot_channels <= 0:
            raise ValueError("max_plot_channels must be greater than zero")


@dataclass(frozen=True)
class DataChunk:
    """One timestamp-aligned chunk received from an inlet."""

    stream_key: str
    samples: tuple[tuple[object, ...], ...]
    remote_timestamps: tuple[float, ...]
    corrected_timestamps: tuple[float, ...]
    host_timestamps: tuple[float, ...]
