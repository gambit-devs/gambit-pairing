"""Shared PyInstaller configuration for the gambit-pairing onedir spec.

Keep plain data structures here so the spec stays small. Release builds stage
two native components before PyInstaller runs:

- the BBP engine, by ``scripts/build_bbp.py`` into
  ``src/gambitpairing/resources/bin``;
- the KDE Breeze style, by ``scripts/stage_breeze.py`` into
  ``build/breeze/<target>``.

``scripts/make_executable.py`` refuses to build when either is missing.
"""

from importlib import metadata
import json
from pathlib import Path
import sys

from PyInstaller.utils.hooks import copy_metadata
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).parent.parent
SRC = ROOT / "src"

sys.path.insert(0, str(Path(__file__).parent))
from stage_breeze import (  # noqa: E402  (needs the scripts directory on sys.path)
    DEFAULT_DEST as BREEZE_STAGE_ROOT,
    STAGE_MANIFEST as BREEZE_STAGE_MANIFEST,
    current_target as breeze_target,
)

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
BBP_BIN_ROOT = SRC / "gambitpairing" / "resources" / "bin"
BBP_BUNDLE_DIR = "gambitpairing/resources/bin"
DATAS.extend(
    (str(notice), BBP_BUNDLE_DIR) for notice in sorted(BBP_BIN_ROOT.glob("BBP-*.txt"))
)
BBP_BINARIES = [
    path
    for path in sorted(BBP_BIN_ROOT.glob("bbpPairings*"))
    if path.is_file() and path.name != "README.txt"
]
BINARIES.extend((str(path), BBP_BUNDLE_DIR) for path in BBP_BINARIES)

# Bundled Qt plugins live in their own directory below sys._MEIPASS. The frozen
# app adds it to Qt's library paths; keep in sync with
# gambitpairing.__main__.BUNDLED_QT_PLUGIN_DIR.
BUNDLED_QT_PLUGIN_DIR = "qt_plugins"
BREEZE_STAGE_DIR = BREEZE_STAGE_ROOT / breeze_target()
BREEZE_BINARIES = []
if (BREEZE_STAGE_DIR / BREEZE_STAGE_MANIFEST).is_file():
    _breeze = json.loads((BREEZE_STAGE_DIR / BREEZE_STAGE_MANIFEST).read_text())
    BREEZE_BINARIES.append(
        (
            str(BREEZE_STAGE_DIR / _breeze["plugin"]),
            f"{BUNDLED_QT_PLUGIN_DIR}/styles",
        )
    )
    # KF6 and helper libraries go to the top-level bundle directory, which the
    # bootloader puts on the library search path (LD_LIBRARY_PATH on Linux,
    # the DLL directory and PATH on Windows).
    BREEZE_BINARIES.extend(
        (str(BREEZE_STAGE_DIR / library), ".") for library in _breeze["libraries"]
    )
    DATAS.append(
        (str(BREEZE_STAGE_DIR / _breeze["notice"]), f"{BUNDLED_QT_PLUGIN_DIR}/")
    )
    # Full license texts, next to the notice: qt_plugins/licenses/<project>/.
    DATAS.extend(
        (
            str(BREEZE_STAGE_DIR / text),
            f"{BUNDLED_QT_PLUGIN_DIR}/{Path(text).parent.as_posix()}/",
        )
        for text in _breeze.get("licenses", [])
    )
BINARIES.extend(BREEZE_BINARIES)

# Licence texts. PyInstaller copies each runtime distribution's dist-info, and
# that carries its licence files. The vendored folders under
# licenses/third_party/overrides/ cover what wheels don't ship: the Python
# runtime (PSF), the GCC runtime exception (Linux bundles libstdc++ and
# libgcc_s) and Velopack, whose wheel has no licence file. See SOURCE.txt in
# each folder. make_executable.py checks the result.
PROJECT = "gambit-pairing"
THIRD_PARTY_BUNDLE_DIR = "gambitpairing/resources/third_party_licenses"
THIRD_PARTY_OVERRIDES = ROOT / "licenses" / "third_party" / "overrides"


def requirement_applies(requirement: Requirement) -> bool:
    """Return True when a requirement is part of the runtime install."""
    if requirement.marker is None:
        return True
    if "extra" in str(requirement.marker):
        return False  # Optional extras are not part of the runtime closure.
    return requirement.marker.evaluate()


def runtime_distributions(root: str = PROJECT) -> dict[str, metadata.Distribution]:
    """Return every distribution the project needs at runtime, keyed by name."""
    closure: dict[str, metadata.Distribution] = {}
    pending = [canonicalize_name(root)]
    while pending:
        name = pending.pop()
        if name in closure:
            continue
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError as error:
            raise RuntimeError(
                f"{name} is not installed; install the project before building."
            ) from error
        closure[name] = dist
        for text in dist.requires or []:
            requirement = Requirement(text)
            if requirement_applies(requirement):
                pending.append(canonicalize_name(requirement.name))
    return closure


RUNTIME_DISTRIBUTIONS = runtime_distributions(PROJECT)
for _name in sorted(RUNTIME_DISTRIBUTIONS):
    if _name != canonicalize_name(PROJECT):
        DATAS.extend(copy_metadata(_name))
DATAS.append(
    (str(THIRD_PARTY_OVERRIDES / "python"), f"{THIRD_PARTY_BUNDLE_DIR}/python")
)
DATAS.append(
    (str(THIRD_PARTY_OVERRIDES / "velopack"), f"{THIRD_PARTY_BUNDLE_DIR}/velopack")
)
if sys.platform.startswith("linux"):
    DATAS.append(
        (
            str(THIRD_PARTY_OVERRIDES / "gcc-runtime"),
            f"{THIRD_PARTY_BUNDLE_DIR}/gcc-runtime",
        )
    )

HIDDENIMPORTS = []
HOOKSPATH = []
RUNTIME_HOOKS = []
# lxml is only a build tool here (breeze-icons uses it when stage_breeze.py
# rebuilds the KDE frameworks); some dependencies import it optionally.
# The test tooling is reached only through lazy imports inside anyio and
# networkx test helpers, which the GUI never calls. Excluding it keeps pytest,
# its plugin hooks and their licences out of the bundle.
EXCLUDES = ["lxml", "pytest", "_pytest", "pluggy", "click", "black"]
NOARCHIVE = False

ICON = str(SRC / "gambitpairing" / "resources" / "icons" / "icon.ico")
APP_NAME = "gambit-pairing"
