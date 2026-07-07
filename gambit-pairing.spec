# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path
from PyInstaller.building.build_main import Analysis, PYZ, EXE

sys.path.insert(0, SPECPATH)
sys.path.insert(0, str(Path(SPECPATH) / "scripts"))

from pyinstaller_common import (
    PATHEX,
    DATAS,
    BINARIES,
    HIDDENIMPORTS,
    HOOKSPATH,
    RUNTIME_HOOKS,
    EXCLUDES,
    NOARCHIVE,
    ICON,
    APP_NAME,
)

a = Analysis(
    ["src/gambitpairing/__main__.py"],
    pathex=PATHEX,
    binaries=BINARIES,
    datas=DATAS,
    hiddenimports=HIDDENIMPORTS,
    hookspath=HOOKSPATH,
    runtime_hooks=RUNTIME_HOOKS,
    excludes=EXCLUDES,
    noarchive=NOARCHIVE,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=APP_NAME,
    icon=ICON,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    optimize=2,
)
