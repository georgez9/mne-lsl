"""Headless tests for channel selection and independent Y-axis scaling."""

from __future__ import annotations

import math
import unittest
from collections import deque

from lsl_gui.models import StreamDescriptor
from lsl_gui.plotting import automatic_y_limits, build_plot_targets, channel_series


class PlottingTests(unittest.TestCase):
    def test_duplicate_channel_labels_remain_independently_selectable(self) -> None:
        descriptors = {
            key: StreamDescriptor(
                key=key,
                name="Repeated",
                stype="EEG",
                source_id="same-source",
                hostname="host",
                n_channels=2,
                sfreq=100.0,
                channel_names=("Signal", "Signal"),
                dtype="float32",
            )
            for key in ("key-a", "key-b")
        }
        targets = build_plot_targets(descriptors)
        self.assertEqual(len(targets), 4)
        self.assertEqual(set(targets.values()), {
            ("key-a", 0), ("key-a", 1), ("key-b", 0), ("key-b", 1)
        })

    def test_channel_series_selects_exact_channel(self) -> None:
        rows = deque(
            [
                (10.0, (1.0, 100.0, 10_000.0)),
                (10.5, (2.0, 200.0, 20_000.0)),
            ]
        )
        times, values = channel_series(rows, 1)
        self.assertEqual(times, [0.0, 0.5])
        self.assertEqual(values, [100.0, 200.0])

    def test_channel_series_ignores_non_finite_values(self) -> None:
        rows = deque([(1.0, (math.nan,)), (2.0, (3.0,)), (3.0, (math.inf,))])
        times, values = channel_series(rows, 0)
        self.assertEqual(times, [1.0])
        self.assertEqual(values, [3.0])

    def test_automatic_y_limits_scale_each_range_independently(self) -> None:
        small = automatic_y_limits([1.0, 2.0])
        large = automatic_y_limits([10_000.0, 20_000.0])
        constant = automatic_y_limits([5.0, 5.0])
        self.assertLess(small[0], 1.0)
        self.assertGreater(small[1], 2.0)
        self.assertLess(large[0], 10_000.0)
        self.assertGreater(large[1], 20_000.0)
        self.assertLess(constant[0], 5.0)
        self.assertGreater(constant[1], 5.0)


if __name__ == "__main__":
    unittest.main()
