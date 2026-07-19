"""PyInstaller specification for the Windows one-file application."""

from importlib.util import find_spec
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_delvewheel_libs_directory,
    collect_dynamic_libs,
)


mne_lsl_spec = find_spec("mne_lsl")
if mne_lsl_spec is None or mne_lsl_spec.submodule_search_locations is None:
    raise RuntimeError("mne_lsl must be installed before building")
mne_lsl_dir = Path(next(iter(mne_lsl_spec.submodule_search_locations)))
lsl_dll = mne_lsl_dir / "lsl" / "lib" / "lsl.dll"
if not lsl_dll.is_file():
    raise RuntimeError(f"Bundled liblsl was not found: {lsl_dll}")
spec_dir = Path(SPECPATH)
project_root = spec_dir.parent
pil_binaries = collect_dynamic_libs("PIL")
pil_datas, pil_binaries = collect_delvewheel_libs_directory(
    "PIL",
    libdir_name="pillow.libs",
    binaries=pil_binaries,
)
mne_stub_data = collect_data_files("mne", includes=["**/*.pyi"])
mne_lsl_stub_data = collect_data_files("mne_lsl", includes=["**/*.pyi"])
mne_data, mne_binaries, mne_hidden = collect_all("mne")
mne_lsl_data, mne_lsl_binaries, mne_lsl_hidden = collect_all("mne_lsl")

analysis = Analysis(
    [str(spec_dir / "launcher.py")],
    pathex=[str(project_root)],
    binaries=[
        (str(lsl_dll), "mne_lsl/lsl/lib"),
        *pil_binaries,
        *mne_binaries,
        *mne_lsl_binaries,
    ],
    datas=[
        *pil_datas,
        *mne_stub_data,
        *mne_lsl_stub_data,
        *mne_data,
        *mne_lsl_data,
    ],
    hiddenimports=[
        "matplotlib.backends.backend_tkagg",
        *mne_hidden,
        *mne_lsl_hidden,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="LSLRecorder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    # The default Windows TEMP path breaks Tcl and native PIL loading on some
    # managed systems. Keep the portable executable in a user-writable folder.
    runtime_tmpdir=".",
)
