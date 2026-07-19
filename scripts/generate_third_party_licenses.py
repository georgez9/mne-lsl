"""Collect license texts from the exact Python environment used for a build."""

from __future__ import annotations

import argparse
import json
import re
import sys
from importlib.metadata import Distribution, distributions
from pathlib import Path
from typing import Iterable

LICENSE_MARKERS = ("license", "copying", "notice")
TEXT_SUFFIXES = ("", ".md", ".rst", ".terms", ".txt")
REQUIRED_DISTRIBUTIONS = {
    "matplotlib",
    "mne",
    "mne-lsl",
    "numpy",
    "pyinstaller",
    "scipy",
}
CONDA_ALIASES = {"mne": "mne-base"}


def _normalized_name(name: str) -> str:
    """Normalize a distribution name for metadata matching."""

    return re.sub(r"[-_.]+", "-", name).lower()


def _conda_versions() -> dict[str, str]:
    """Return exact Conda package versions when running inside Conda."""

    versions: dict[str, str] = {}
    metadata_dir = Path(sys.prefix) / "conda-meta"
    for path in metadata_dir.glob("*.json"):
        try:
            metadata = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        name = metadata.get("name")
        version = metadata.get("version")
        if isinstance(name, str) and isinstance(version, str):
            versions[_normalized_name(name)] = version
    return versions


def _conda_license_files() -> dict[str, tuple[Path, ...]]:
    """Return full license files retained in the local Conda package cache."""

    results: dict[str, tuple[Path, ...]] = {}
    metadata_dir = Path(sys.prefix) / "conda-meta"
    for path in metadata_dir.glob("*.json"):
        try:
            metadata = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        name = metadata.get("name")
        package_dir = metadata.get("extracted_package_dir")
        if not isinstance(name, str) or not isinstance(package_dir, str):
            continue
        license_dir = Path(package_dir) / "info" / "licenses"
        files = tuple(item for item in license_dir.rglob("*") if item.is_file())
        if files:
            results[_normalized_name(name)] = files
    return results


def _license_files(distribution: Distribution) -> Iterable[Path]:
    """Yield installed license-like files for one distribution."""

    for entry in distribution.files or ():
        name = Path(str(entry)).name.lower()
        suffix = Path(name).suffix
        if name.startswith(LICENSE_MARKERS) and suffix in TEXT_SUFFIXES:
            path = Path(distribution.locate_file(entry))
            if path.is_file():
                yield path


def _runtime_license_files() -> Iterable[tuple[str, Path]]:
    """Yield Python and Tcl/Tk runtime license files when installed."""

    candidates = (
        ("Python", Path(sys.base_prefix) / "LICENSE.txt"),
        ("Python", Path(sys.base_prefix) / "LICENSE_PYTHON.txt"),
        ("Tcl", Path(sys.base_prefix) / "tcl" / "tcl8.6" / "license.terms"),
        ("Tk", Path(sys.base_prefix) / "tcl" / "tk8.6" / "license.terms"),
        ("Tcl", Path(sys.base_prefix) / "Library" / "lib" / "tcl8.6" / "license.terms"),
        ("Tk", Path(sys.base_prefix) / "Library" / "lib" / "tk8.6" / "license.terms"),
    )
    return ((name, path) for name, path in candidates if path.is_file())


def _bundled_license_files() -> Iterable[tuple[str, Path]]:
    """Yield audited licenses for native components bundled by the project."""

    license_dir = Path(__file__).resolve().parent.parent / "licenses"
    return (
        (path.stem, path)
        for path in sorted(license_dir.glob("*-LICENSE.*"))
        if path.is_file()
    )


def generate(output: Path) -> int:
    """Write exact installed versions and available license texts to output."""

    sections = [
        "THIRD-PARTY LICENSES",
        "Generated from the Python environment used to build LSLRecorder.",
    ]
    seen: set[tuple[str, str]] = set()
    conda_versions = _conda_versions()
    conda_licenses = _conda_license_files()
    distributions_with_full_text: set[str] = set()
    count = 0
    for distribution in sorted(
        distributions(),
        key=lambda item: (item.metadata.get("Name", "").lower(), item.version),
    ):
        name = distribution.metadata.get("Name") or "unknown"
        version = conda_versions.get(_normalized_name(name), distribution.version)
        key = (name.lower(), version)
        if key in seen:
            continue
        seen.add(key)
        texts: list[str] = []
        for path in _license_files(distribution):
            texts.append(path.read_text(encoding="utf-8", errors="replace").strip())
        conda_name = CONDA_ALIASES.get(
            _normalized_name(name),
            _normalized_name(name),
        )
        if not texts:
            for path in conda_licenses.get(conda_name, ()):
                texts.append(
                    path.read_text(encoding="utf-8", errors="replace").strip()
                )
        if texts:
            distributions_with_full_text.add(_normalized_name(name))
        if not texts:
            metadata_license = distribution.metadata.get("License-Expression")
            metadata_license = metadata_license or distribution.metadata.get("License")
            if metadata_license and len(metadata_license.strip()) > 1:
                texts.append(metadata_license.strip())
        if not texts:
            continue
        count += 1
        sections.extend(
            [
                "",
                "=" * 78,
                f"{name} {version}",
                "=" * 78,
                "\n\n".join(dict.fromkeys(texts)),
            ]
        )

    runtime_files = tuple(_runtime_license_files())
    bundled_files = tuple(_bundled_license_files())
    for name, path in (*runtime_files, *bundled_files):
        count += 1
        sections.extend(
            [
                "",
                "=" * 78,
                name,
                "=" * 78,
                path.read_text(encoding="utf-8", errors="replace").strip(),
            ]
        )

    missing_distributions = sorted(
        REQUIRED_DISTRIBUTIONS - distributions_with_full_text
    )
    runtime_names = {name for name, _ in runtime_files}
    bundled_names = {name for name, _ in bundled_files}
    missing_runtime = []
    if "Python" not in runtime_names:
        missing_runtime.append("Python")
    if "liblsl-LICENSE" not in bundled_names:
        missing_runtime.append("liblsl")
    if "tcl-tk-LICENSE" not in bundled_names:
        missing_runtime.append("Tcl/Tk")
    if missing_distributions or missing_runtime:
        missing = ", ".join((*missing_distributions, *missing_runtime))
        raise RuntimeError(f"Required full license text was not found for: {missing}")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(sections) + "\n", encoding="utf-8")
    return count


def main() -> None:
    """Parse command-line arguments and generate the notice bundle."""

    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    count = generate(args.output)
    if count == 0:
        raise RuntimeError("No dependency license text was found")
    print(f"Collected license text for {count} installed components.")


if __name__ == "__main__":
    main()
