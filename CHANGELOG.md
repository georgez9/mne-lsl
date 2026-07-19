# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.1.1] - 2026-07-20

### Fixed

- Pin the Windows release to Pillow 11.3.0 and collect PIL native binaries.
- Include MNE and MNE-LSL type stubs required by their frozen lazy loaders.
- Collect MNE and MNE-LSL lazy-loaded modules and package data for frozen builds.
- Avoid native-library and Tcl loading failures from the default Windows temp directory.
- Make packaged smoke tests wait for the windowed process and validate its real
  exit code and diagnostic report.

## [0.1.0] - 2026-07-20

- Add discovery, connection, recording, saving, and disconnection for multiple LSL streams.
- Add three independently selectable, auto-scaling waveform panels.
- Add synthetic multi-stream testing without physical hardware.
- Add Windows one-file packaging and tag-based GitHub Releases.
