"""Tests for fail-closed release license collection."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.generate_third_party_licenses import (
    _bundled_license_files,
    generate,
)


class ReleaseLicenseTests(unittest.TestCase):
    def test_audited_native_licenses_are_present(self) -> None:
        names = {name for name, _ in _bundled_license_files()}
        self.assertIn("liblsl-LICENSE", names)
        self.assertIn("tcl-tk-LICENSE", names)

    @patch("scripts.generate_third_party_licenses.distributions", return_value=())
    @patch("scripts.generate_third_party_licenses._conda_versions", return_value={})
    @patch(
        "scripts.generate_third_party_licenses._conda_license_files",
        return_value={},
    )
    def test_required_distribution_license_cannot_be_skipped(
        self,
        _conda_licenses: object,
        _conda_versions: object,
        _distributions: object,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(RuntimeError, "Required full license text"):
                generate(Path(temp_dir) / "licenses.txt")


if __name__ == "__main__":
    unittest.main()
