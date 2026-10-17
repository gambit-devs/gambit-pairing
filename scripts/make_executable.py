#!/usr/bin/env python3
"""Build the Gambit Pairing onedir application with PyInstaller.

Release builds are onedir only: Velopack packs and updates a directory, and the
portable archives are made from the same directory.

Usage:
  python scripts/make_executable.py               # build dist/gambit-pairing/
  python scripts/make_executable.py --skip-deps   # do not run ensure_all_dependencies.py

Before building, stage the native components:
  python scripts/build_bbp.py        # BBP engine -> src/gambitpairing/resources/bin
  python scripts/stage_breeze.py     # Breeze style -> build/breeze/<target>
"""

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
SPEC_FILE = ROOT / "gambit-pairing-onedir.spec"
APP_NAME = "gambit-pairing"

sys.path.insert(0, str(SCRIPTS))
from packaging.utils import canonicalize_name  # noqa: E402
import pyinstaller_common  # noqa: E402  (needs the scripts directory on sys.path)


class BuildError(Exception):
    """A build precondition or postcondition failed."""


def run_command(cmd, description, env=None):
    """Run a command, streaming its output; exit on failure."""
    print(f"Running: {description}", flush=True)
    try:
        subprocess.run(cmd, check=True, env=env)
    except subprocess.CalledProcessError as error:
        raise BuildError(f"{description} failed with exit code {error.returncode}")
    except FileNotFoundError:
        raise BuildError(f"Command not found: {cmd[0]}")


def ensure_dependencies():
    """Ensure all dependencies are installed."""
    run_command(
        [sys.executable, str(SCRIPTS / "ensure_all_dependencies.py")],
        "Installing dependencies",
    )


def check_staged_components() -> None:
    """Refuse to build without the engine or without Breeze."""
    if not pyinstaller_common.BBP_BINARIES:
        raise BuildError(
            "The BBP engine is not staged in "
            f"{pyinstaller_common.BBP_BIN_ROOT}. Run python scripts/build_bbp.py first."
        )
    if not pyinstaller_common.BREEZE_BINARIES:
        raise BuildError(
            "The Breeze style is not staged in "
            f"{pyinstaller_common.BREEZE_STAGE_DIR}. Run python scripts/stage_breeze.py first."
        )


def pyinstaller_env() -> dict:
    """Make PyInstaller resolve Qt and KF6 libraries from the bundled runtime.

    Breeze's KF6 libraries link against Qt modules (Quick, Qml, ...) that PyQt6
    itself does not import. Without this, PyInstaller can resolve them from a
    host Qt installation, which is a different and incompatible Qt build.
    """
    env = dict(os.environ)
    try:
        import PyQt6
    except ImportError:
        return env
    qt_dir = Path(PyQt6.__file__).resolve().parent / "Qt6"
    breeze_lib = pyinstaller_common.BREEZE_STAGE_DIR / "lib"
    if sys.platform.startswith("linux"):
        variable, paths = "LD_LIBRARY_PATH", [qt_dir / "lib", breeze_lib]
    elif sys.platform == "win32":
        variable, paths = "PATH", [qt_dir / "bin", breeze_lib]
    else:
        variable, paths = "DYLD_LIBRARY_PATH", [breeze_lib]
    existing = [env[variable]] if env.get(variable) else []
    env[variable] = os.pathsep.join([str(path) for path in paths] + existing)
    return env


def check_licence_texts(internal: Path) -> None:
    """Refuse a bundle that is missing a licence text it must ship.

    PyInstaller copies the Qt licence with its dist-info; the other texts are
    the vendored overrides. The Linux bundle also needs the GCC runtime
    exception, because it ships libstdc++ and libgcc_s.
    """
    licence_dir = internal / pyinstaller_common.THIRD_PARTY_BUNDLE_DIR
    required = [
        licence_dir / "python" / "LICENSE.txt",
        licence_dir / "velopack" / "LICENSE",
    ]
    if sys.platform.startswith("linux"):
        required.append(licence_dir / "gcc-runtime" / "COPYING.RUNTIME")
    missing = [
        str(path.relative_to(internal)) for path in required if not path.is_file()
    ]
    if not list(internal.glob("pyqt6_qt6*.dist-info/LICENSE")):
        missing.append("pyqt6_qt6*.dist-info/LICENSE")
    if missing:
        raise BuildError(
            f"Licence texts are missing from {internal}: {', '.join(missing)}"
        )


def bundled_distribution_names(internal: Path) -> set[str]:
    """Return the canonical names of distributions PyInstaller copied metadata for."""
    names = set()
    for metadata_file in internal.glob("*.dist-info/METADATA"):
        text = metadata_file.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if line.startswith("Name: "):
                names.add(canonicalize_name(line[len("Name: ") :].strip()))
                break
    return names


def check_bundled_distributions(internal: Path) -> None:
    """Refuse a bundle that ships a distribution whose licence was not collected."""
    expected = set(pyinstaller_common.RUNTIME_DISTRIBUTIONS)
    extra = bundled_distribution_names(internal) - expected
    if extra:
        raise BuildError(
            "The bundle contains distributions outside the runtime closure, so their "
            f"licences were not collected: {', '.join(sorted(extra))}. Remove them "
            "from the bundle or add them to the project's dependencies."
        )


def expected_executable(dist: Path) -> Path:
    suffix = ".exe" if sys.platform == "win32" else ""
    return dist / APP_NAME / f"{APP_NAME}{suffix}"


def verify_bundle(dist: Path) -> None:
    """Check the onedir bundle has the app, the engine, Breeze and its licenses."""
    exe = expected_executable(dist)
    if not exe.is_file():
        raise BuildError(f"Expected executable not found: {exe}")
    bundle = dist / APP_NAME
    engines = list(bundle.rglob("bbpPairings*"))
    if not engines:
        raise BuildError(f"The BBP engine is missing from {bundle}")
    plugin_dir = bundle / "_internal" / pyinstaller_common.BUNDLED_QT_PLUGIN_DIR
    styles = list((plugin_dir / "styles").glob("breeze6*"))
    if not styles:
        raise BuildError(f"The Breeze style plugin is missing from {plugin_dir}")
    if not list((plugin_dir / "licenses").glob("*/*")):
        raise BuildError(f"The Breeze license texts are missing from {plugin_dir}")
    internal = bundle / "_internal"
    check_licence_texts(internal)
    check_bundled_distributions(internal)
    size_mb = exe.stat().st_size / (1024 * 1024)
    print(f"[+] Onedir executable: {exe} ({size_mb:.1f} MB)")
    for engine in engines:
        print(f"[+] Engine: {engine.relative_to(dist)}")
    for style in styles:
        print(f"[+] Breeze: {style.relative_to(dist)}")


def build() -> None:
    check_staged_components()
    run_command(
        [sys.executable, "-m", "PyInstaller", "--clean", "-y", str(SPEC_FILE)],
        f"PyInstaller ({SPEC_FILE.name})",
        env=pyinstaller_env(),
    )
    verify_bundle(ROOT / "dist")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the Gambit Pairing onedir executable with PyInstaller",
    )
    parser.add_argument(
        "--skip-deps", action="store_true", help="Skip dependency installation check"
    )
    args = parser.parse_args(argv)
    os.chdir(ROOT)

    print("Gambit Pairing - Executable Builder")
    print("=" * 40)
    try:
        if not args.skip_deps:
            ensure_dependencies()
        build()
    except BuildError as error:
        print(f"[x] {error}", file=sys.stderr)
        return 1
    print("\nBuild completed successfully!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#  LocalWords:  onedir
