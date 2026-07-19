"""PyInstaller specification for the Windows one-file application."""

from importlib.util import find_spec
from pathlib import Path


mne_lsl_spec = find_spec("mne_lsl")
if mne_lsl_spec is None or mne_lsl_spec.submodule_search_locations is None:
    raise RuntimeError("mne_lsl must be installed before building")
mne_lsl_dir = Path(next(iter(mne_lsl_spec.submodule_search_locations)))
lsl_dll = mne_lsl_dir / "lsl" / "lib" / "lsl.dll"
if not lsl_dll.is_file():
    raise RuntimeError(f"Bundled liblsl was not found: {lsl_dll}")
spec_dir = Path(SPECPATH)
project_root = spec_dir.parent

analysis = Analysis(
    [str(spec_dir / "launcher.py")],
    pathex=[str(project_root)],
    binaries=[(str(lsl_dll), "mne_lsl/lsl/lib")],
    datas=[],
    hiddenimports=["matplotlib.backends.backend_tkagg"],
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
)
