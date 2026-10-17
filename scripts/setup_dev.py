#!/usr/bin/env python3
"""Create an isolated editable Python environment for Gambit development.

This script does not install system packages. Run it as your normal user,
without sudo. It works on Linux, macOS and Windows and uses only the standard
library so a bare system Python can run it.
"""

import argparse
import glob
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

PROJECT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_DIR / "scripts"
# Keep this in sync with requires-python in pyproject.toml.
MINIMUM_PYTHON = (3, 10)
MINIMUM_PYTHON_TEXT = ".".join(str(part) for part in MINIMUM_PYTHON)

PROBE_CODE = (
    "import os, sys; "
    "print(os.path.realpath(getattr(sys, '_base_executable', sys.executable))); "
    "print('%s.%s.%s' % sys.version_info[:3])"
)
BREEZE_PROBE_CODE = """\
from PyQt6.QtWidgets import QApplication
from gambitpairing.__main__ import configure_native_style

app = QApplication([])
raise SystemExit(configure_native_style(app).casefold() != "breeze")
"""
SYSTEM_SITE_FALSE = re.compile(
    r"^include-system-site-packages\s*=\s*false\s*$", re.MULTILINE
)

BBP_NOTE = (
    "The optional BBP reference engine is not built; Gambit will use its native "
    "fallback. Build it with 'python scripts/build_bbp.py' when needed."
)
BREEZE_NOTE = (
    "The venv's Qt could not load a Breeze style plugin, so Gambit will use "
    "another Qt style. A system Breeze package only loads here if it was built "
    "for a Qt compatible with the pip-installed PyQt6; release builds bundle "
    "their own Breeze."
)


class SetupError(Exception):
    """A fatal setup problem with a message for the user."""


def is_windows(platform: str) -> bool:
    return platform == "win32"


def is_linux(platform: str) -> bool:
    return platform.startswith("linux")


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="scripts/setup_dev.py",
        description=(
            "Create an isolated editable Python environment. This script does not "
            "install system packages. Run it as your normal user, without sudo."
        ),
    )
    parser.add_argument(
        "--python",
        metavar="PATH",
        help=f"Use this Python interpreter (Python {MINIMUM_PYTHON_TEXT} or newer).",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Remove and recreate the project's ignored .venv directory.",
    )
    parser.add_argument(
        "--build-bbp",
        action="store_true",
        help="Build the optional BBP engine (requires existing make/g++).",
    )
    parser.add_argument(
        "--require-breeze",
        action="store_true",
        help="Fail if Qt cannot load the Breeze Widgets style (Breeze is Linux-only).",
    )
    args = parser.parse_args(argv)
    if args.python is not None and not args.python:
        parser.error("--python needs an interpreter path.")
    return args


def venv_bin_dir(venv_dir: Path, platform: str) -> Path:
    return venv_dir / ("Scripts" if is_windows(platform) else "bin")


def venv_python_path(venv_dir: Path, platform: str) -> Path:
    name = "python.exe" if is_windows(platform) else "python"
    return venv_bin_dir(venv_dir, platform) / name


def launcher_path(venv_dir: Path, platform: str) -> Path:
    name = "gambit-pairing.exe" if is_windows(platform) else "gambit-pairing"
    return venv_bin_dir(venv_dir, platform) / name


def python_candidates(platform: str, glob_fn=glob.glob) -> list:
    """Return interpreter commands (argv prefixes) to try, best first."""
    if is_windows(platform):
        return [["py", "-3"], ["python"]]
    system = [["/usr/bin/python3"]] + [
        [path] for path in sorted(glob_fn("/usr/bin/python3.[0-9]*"))
    ]
    on_path = [["python3"], ["python"]]
    if is_linux(platform):
        # Prefer system interpreters; activated venvs are unwrapped anyway.
        return system + on_path
    # On macOS /usr/bin/python3 may be a stub that offers to install the
    # Command Line Tools, so try the user's PATH first.
    return on_path + system


def version_is_compatible(version: str) -> bool:
    try:
        major, minor = (int(part) for part in version.split(".")[:2])
    except ValueError:
        return False
    return (major, minor) >= MINIMUM_PYTHON


def probe_python(command: list, run=subprocess.run):
    """Run an interpreter and return (resolved base executable, version).

    Returns None when it cannot run, which also catches Windows Store stubs.
    """
    if shutil.which(command[0]) is None:
        return None
    try:
        result = run(
            command + ["-c", PROBE_CODE],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    lines = result.stdout.strip().splitlines()
    if result.returncode != 0 or len(lines) != 2:
        return None
    return lines[0].strip(), lines[1].strip()


def find_python(requested, platform: str, probe=probe_python):
    """Return (python_bin, old_python_version) for the first usable candidate."""
    candidates = [[requested]] if requested else python_candidates(platform)
    old_version = None
    for command in candidates:
        probed = probe(command)
        if probed is None:
            continue
        resolved, version = probed
        if version_is_compatible(version):
            return resolved, old_version
        if old_version is None:
            old_version = version
    if old_version is not None:
        raise SetupError(
            f"Python {old_version} is older than Gambit's required Python "
            f"{MINIMUM_PYTHON_TEXT}. Install a newer Python, then rerun with "
            "--python /path/to/python3."
        )
    if requested:
        raise SetupError(f"Cannot run the requested Python interpreter: {requested}")
    raise SetupError(
        f"Python {MINIMUM_PYTHON_TEXT} or newer is required. Install it for your "
        "user, then rerun with --python /path/to/python3 if needed."
    )


def check_privileges(platform: str, environ=os.environ, geteuid=None) -> None:
    if is_windows(platform):
        return
    euid = (geteuid or os.geteuid)()
    if euid == 0 and (environ.get("SUDO_USER") or environ.get("DOAS_USER")):
        raise SetupError(
            "Run this script without sudo/doas; it only creates a user-owned .venv "
            "and does not install system packages."
        )


def venv_is_usable(venv_dir: Path, platform: str, probe=probe_python) -> bool:
    """Check an existing venv is intact, isolated and new enough."""
    config = venv_dir / "pyvenv.cfg"
    python = venv_python_path(venv_dir, platform)
    if not config.is_file() or not python.is_file():
        return False
    try:
        text = config.read_text(encoding="utf-8")
    except OSError:
        return False
    if not SYSTEM_SITE_FALSE.search(text):
        return False
    probed = probe([str(python)])
    return probed is not None and version_is_compatible(probed[1])


def check_existing_venv(
    venv_dir: Path, platform: str, recreate: bool, probe=probe_python
) -> None:
    if venv_dir.is_symlink():
        raise SetupError(
            f"{venv_dir} is a symlink. Use a local .venv directory instead."
        )
    if not venv_dir.exists():
        return
    if not os.access(venv_dir, os.W_OK):
        raise SetupError(
            f"{venv_dir} is not writable by this account. Remove it with its owner, "
            "then rerun setup as your normal user."
        )
    if not recreate and not venv_is_usable(venv_dir, platform, probe):
        raise SetupError(
            f"{venv_dir} is broken, outdated, or uses system packages. "
            "Rerun with --recreate."
        )


def same_path(left: str, right: str) -> bool:
    return os.path.normcase(os.path.realpath(left)) == os.path.normcase(
        os.path.realpath(right)
    )


def create_venv(venv_dir: Path, python_bin: str, recreate: bool) -> None:
    if recreate and venv_dir.exists():
        shutil.rmtree(venv_dir)
    if not venv_dir.exists():
        result = subprocess.run([python_bin, "-m", "venv", str(venv_dir)])
        if result.returncode != 0:
            raise SetupError(
                "Could not create .venv. Install this Python's venv/ensurepip "
                "support and rerun."
            )


def check_venv_base(venv_python: Path, python_bin: str, probe=probe_python) -> None:
    probed = probe([str(venv_python)])
    if probed is None or not same_path(probed[0], python_bin):
        raise SetupError(
            f".venv uses a different Python. Rerun with --recreate to use {python_bin}."
        )


def quiet_ok(command: list) -> bool:
    result = subprocess.run(
        command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    return result.returncode == 0


def ensure_pip(venv_python: Path, venv_dir: Path) -> None:
    python = str(venv_python)
    if quiet_ok([python, "-m", "pip", "--version"]):
        return
    if quiet_ok([python, "-m", "ensurepip", "--version"]):
        subprocess.run([python, "-m", "ensurepip", "--upgrade"], check=True)
        return
    uv = shutil.which("uv")
    if uv:
        subprocess.run([uv, "pip", "install", "--python", python, "pip"], check=True)
        return
    raise SetupError(
        f"Could not bootstrap pip in {venv_dir}. Enable ensurepip for this Python "
        "or install uv."
    )


def bbp_engine_available(project_dir: Path, which=shutil.which) -> bool:
    staged = project_dir / "src" / "gambitpairing" / "resources" / "bin"
    if any(path.is_file() for path in staged.glob("bbpPairings*")):
        return True
    return bool(which("bbpPairings.exe") or which("bbpPairings"))


def qt_check_env(require_breeze: bool, environ=os.environ) -> dict:
    env = dict(environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["GAMBIT_NATIVE_STYLE_REQUIRED"] = "1" if require_breeze else "0"
    return env


def breeze_available(venv_python: Path, env: dict) -> bool:
    result = subprocess.run([str(venv_python), "-c", BREEZE_PROBE_CODE], env=env)
    return result.returncode == 0


def old_python_note(old_version: str, python_bin: str) -> str:
    return f"Python {old_version} was also found; this environment uses {python_bin}."


def format_notes(notes: list) -> str:
    return "".join(f"\nNote: {note}\n" for note in notes)


def run_setup(args: argparse.Namespace, platform: str = sys.platform) -> None:
    check_privileges(platform)
    os.chdir(PROJECT_DIR)
    # Keep user site packages and an activated environment from leaking into setup.
    os.environ["PYTHONNOUSERSITE"] = "1"
    os.environ.pop("PYTHONHOME", None)
    os.environ.pop("PYTHONPATH", None)

    notes = []
    python_bin, old_version = find_python(args.python, platform)

    venv_dir = PROJECT_DIR / ".venv"
    check_existing_venv(venv_dir, platform, args.recreate)
    create_venv(venv_dir, python_bin, args.recreate)

    venv_python = venv_python_path(venv_dir, platform)
    check_venv_base(venv_python, python_bin)
    ensure_pip(venv_python, venv_dir)

    install = subprocess.run(
        [str(venv_python), str(SCRIPTS_DIR / "install_editable_pip.py")]
    )
    if install.returncode != 0:
        raise SetupError("The editable install failed. Check the output above.")

    if args.build_bbp:
        # build_bbp.py checks for its own toolchain (make and g++).
        build = subprocess.run([str(venv_python), str(SCRIPTS_DIR / "build_bbp.py")])
        if build.returncode != 0:
            raise SetupError(
                "Building the BBP engine failed. --build-bbp requires GNU make and a "
                "C++20-capable g++; install those tools yourself and rerun."
            )
    elif not bbp_engine_available(PROJECT_DIR):
        notes.append(BBP_NOTE)

    print("Checking the Qt runtime...", flush=True)
    env = qt_check_env(args.require_breeze)
    # Use -m rather than the GUI launcher so output is visible on Windows.
    qt_check = subprocess.run(
        [str(venv_python), "-m", "gambitpairing", "--verify-native-style"], env=env
    )
    if qt_check.returncode != 0:
        raise SetupError(
            "Gambit's Qt runtime check failed. Check the output above for missing "
            "Qt runtime dependencies."
        )
    # Breeze is a Linux (KDE) style; other platforms use their native style.
    probe_env = qt_check_env(require_breeze=False)
    if is_linux(platform) and not breeze_available(venv_python, probe_env):
        notes.append(BREEZE_NOTE)

    print()
    print("Development environment is ready.")
    print(f'Run Gambit with: "{launcher_path(venv_dir, platform)}"')
    if old_version is not None:
        notes.append(old_python_note(old_version, python_bin))
    print(format_notes(notes), end="")


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        run_setup(args)
    except SetupError as error:
        print(error, file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        print(f"Command failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
