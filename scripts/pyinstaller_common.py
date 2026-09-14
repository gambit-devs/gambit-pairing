"""Shared PyInstaller configuration for gambit-pairing specs.

Keep plain data structures here so both spec files can import them and stay small.
"""

from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = ROOT / "src"

# Where PyInstaller should look for imports (adjust if your layout changes)
PATHEX = [str(SRC)]

# Data files to include (source path or glob, destination relative path inside bundle)
DATAS = [
    (str(ROOT / "licenses" / "LICENSE"), "gambitpairing/resources/"),
    (
        str(SRC / "gambitpairing" / "ui" / "*.ui"),
        "gambitpairing/ui/",
    ),
]

_ICON_ROOT = SRC / "gambitpairing" / "resources" / "icons"
for _icon_pattern in ("*.png", "*.ico", "*.webp"):
    DATAS.extend(
        (str(icon_path), "gambitpairing/resources/icons/")
        for icon_path in sorted(_ICON_ROOT.glob(_icon_pattern))
    )

BINARIES = []
_BBP_BIN_ROOT = SRC / "gambitpairing" / "resources" / "bin"
for _bbp_binary in sorted(_BBP_BIN_ROOT.glob("bbpPairings*")):
    if _bbp_binary.is_file() and _bbp_binary.name != "README.txt":
        BINARIES.append((str(_bbp_binary), "gambitpairing/resources/bin"))
HIDDENIMPORTS = []
HOOKSPATH = []
RUNTIME_HOOKS = []
EXCLUDES = []
NOARCHIVE = False

ICON = str(SRC / "gambitpairing" / "resources" / "icons" / "icon.ico")
APP_NAME = "gambit-pairing"
