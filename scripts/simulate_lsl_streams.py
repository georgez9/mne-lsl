"""Publish a bundled demo outlet expanded by the GUI into three test streams."""

from __future__ import annotations

import math
import time
from argparse import ArgumentParser

import numpy as np

from mne_lsl.lsl import StreamInfo, StreamOutlet, local_clock


def main(duration: float | None = None) -> None:
    """Publish EEG, auxiliary sensor, and event-code channels in one outlet."""

    channel_names = [
        "Fz",
        "C3",
        "C4",
        "Pz",
        "Respiration",
        "Temperature",
        "EventCode",
    ]
    info = StreamInfo(
        "Demo-Bundle",
        "Demo",
        len(channel_names),
        100.0,
        "float32",
        "demo-bundle-source",
    )
    info.set_channel_names(channel_names)
    outlet = StreamOutlet(info, chunk_size=10)
    start = local_clock()
    deadline = None if duration is None else time.monotonic() + duration
    print("Synthetic Demo-EEG, Demo-Aux, and Demo-Events views are running.")
    print("Press Ctrl+C to stop.")
    try:
        while deadline is None or time.monotonic() < deadline:
            now = local_clock()
            elapsed = now - start
            event_code = float(int(elapsed) % 4) if int(elapsed * 10) % 10 == 0 else 0.0
            sample = np.asarray(
                [
                    *(math.sin(2 * math.pi * frequency * elapsed) for frequency in (8, 10, 12, 15)),
                    2.0 + 0.4 * math.sin(2 * math.pi * 0.25 * elapsed),
                    36.5 + 0.1 * math.sin(2 * math.pi * 0.05 * elapsed),
                    event_code,
                ],
                dtype=np.float32,
            )
            outlet.push_sample(sample, timestamp=now)
            time.sleep(0.01)
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=float, default=None)
    arguments = parser.parse_args()
    main(arguments.duration)
