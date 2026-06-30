"""Shared PyInstaller configuration for gambit-pairing specs.

Keep plain data structures here so both spec files can import them and stay small.
"""

from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "src"

# Where PyInstaller should look for imports (adjust if your layout changes)
PATHEX = [str(SRC)]

# Data files to include (source path or glob, destination relative path inside bundle)
DATAS = [
    # styles.qss no longer shipped; individual partials are compiled at runtime
    (str(SRC / "gambitpairing" / "resources" / "LICENSE"), "gambitpairing/resources/"),
    (
        str(SRC / "gambitpairing" / "resources" / "styles" / "*.qss"),
        "gambitpairing/resources/styles/",
    ),
    (
        str(SRC / "gambitpairing" / "resources" / "icons" / "*"),
        "gambitpairing/resources/icons/",
    ),
    (
        str(SRC / "gambitpairing" / "ui" / "*.ui"),
        "gambitpairing/ui/",
    ),
]

BINARIES = []
HIDDENIMPORTS = []
HOOKSPATH = []
RUNTIME_HOOKS = []
EXCLUDES = []
NOARCHIVE = False

ICON = str(SRC / "gambitpairing" / "resources" / "icons" / "icon.ico")
APP_NAME = "gambit-pairing"
