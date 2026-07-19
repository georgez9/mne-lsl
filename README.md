# LSL Recorder

[English](README.md) | [简体中文](README.zh-CN.md)

A lightweight desktop recording tool for EEG, eye-tracking, markers, and other
Lab Streaming Layer (LSL) data sources.

## Features

- Automatically discovers visible LSL streams without relying on hard-coded device names.
- Connects to a stream when selected and disconnects when deselected.
- Starts and stops multiple connected streams together and saves each stream to a separate CSV file.
- Provides three independent waveform plots, each with selectable channels and automatic Y-axis scaling for visible data.
- Saves a session manifest and preserves unconfirmed recording data after an unexpected exit.
- Includes a multi-stream simulator for testing without hardware.

## Use the Windows EXE

Official builds are published on [GitHub Releases](https://github.com/georgez9/mne-lsl/releases).
Download `LSLRecorder.exe` and run it directly; Python is not required. Recordings
are saved to the following directory by default:

Place the EXE in a writable folder, such as `Downloads\LSLRecorder`, before
running it. Do not launch it directly from a read-only directory, archive
preview, or network share.

```text
Documents\LSL Recorder\Data
```

Logs are written to `Documents\LSL Recorder\logs`. You can select a different
output directory in the GUI or override the default with the
`LSL_RECORDER_DATA_DIR` environment variable.

## Run from Source

Conda is recommended:

```powershell
conda env create -f environment.yml
conda activate mne-lsl
python -m lsl_gui
```

You can also run `run_lsl_gui.bat`. The basic workflow is: discover streams →
select to connect → start reading → stop reading → save. Deselecting a stream
disconnects it.

## Test Without Hardware

Double-click `run_demo.bat` to start simulated streams and open the GUI. You can
also run the components separately:

```powershell
python scripts/simulate_lsl_streams.py
python -m lsl_gui
```

The GUI will show three independently connectable logical streams:
`Demo-EEG`, `Demo-Aux`, and `Demo-Events`. Use them to test multi-stream
connections, three-channel waveform selection, recording, saving, and
disconnection.

## Testing and Building

```powershell
python -m unittest discover -s tests -v
python -m pip install -r requirements-build.txt
.\scripts\build_release.ps1 -Python python
```

Build artifacts are written to `dist/` and are not committed to Git. See the
[release guide](docs/release-guide.md) for the complete release process.

## Repository Structure

```text
.github/workflows/  CI and tag-based release workflows
build_tools/        PyInstaller entry point and spec
docs/               Sharing and release documentation
lsl_gui/            Application source code
scripts/            Simulator and build scripts
tests/              Hardware-independent unit tests
```

Local recording data, `legacy/`, `plan/`, IDE settings, environment directories,
and build artifacts are ignored by Git. See the
[repository policy](docs/repository-policy.md) for details.

## License

This project is licensed under the [MIT License](LICENSE). Third-party components
remain subject to their respective licenses; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for details.
