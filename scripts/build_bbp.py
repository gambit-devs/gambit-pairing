"""Build the pinned BBP source and stage the engine for application packaging.

Installing the Python package never runs this script; release builds and
developers who want the BBP engine run it explicitly.

Toolchains:
- Linux: GNU make and a C++20-capable g++ (on Kinoite, run it in Toolbox).
- Windows: MSYS2 UCRT64 (mingw-w64 g++ and make), run from the MSYS2 shell.
  This is the toolchain upstream BBP uses (see vendor/bbp/packaging/mingw-w64);
  the MinGW-w64 runtime license is appended to the staged BBP license.
- macOS: Xcode command line tools (make and clang++); pass --comp clang.

No downloads, host package installation or compilation occur at app startup.
"""

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

BBP_VERSION = "v6.0.0"


def default_comp(platform: str = sys.platform) -> str:
    return "clang" if platform == "darwin" else "gcc"


def find_make(requested=None, which=shutil.which):
    if requested:
        return which(requested)
    return which("make") or which("mingw32-make")


def make_command(make, source, jobs, target, comp, static):
    command = [
        make,
        "-C",
        str(source),
        f"-j{jobs}",
        f"version={BBP_VERSION}",
        f"COMP={comp}",
    ]
    if static:
        command.append("static=yes")
    command.append(target)
    return command


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true", help="Run upstream C++ tests")
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument(
        "--comp",
        choices=("gcc", "clang"),
        default=default_comp(),
        help="Compiler family passed to the BBP Makefile (default: %(default)s)",
    )
    parser.add_argument(
        "--static",
        action="store_true",
        help=(
            "Link statically (Windows release builds, so no MinGW runtime DLLs "
            "are needed; on Linux this needs static glibc and libstdc++)"
        ),
    )
    parser.add_argument("--make", help="make executable to use (default: make)")
    args = parser.parse_args(argv)
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    if args.static and sys.platform == "darwin":
        parser.error("--static is not supported on macOS")
    make = find_make(args.make)
    compiler = "clang++" if args.comp == "clang" else "g++"
    if not make or not shutil.which(compiler):
        parser.error(
            f"make and {compiler} are required; on Kinoite run this script in "
            "Toolbox, on Windows run it from the MSYS2 UCRT64 shell"
        )
    root = Path(__file__).resolve().parents[1]
    source = root / "vendor" / "bbp"
    subprocess.run(
        make_command(
            make,
            source,
            args.jobs,
            "test" if args.test else "all",
            args.comp,
            args.static,
        ),
        check=True,
    )
    destination = root / "src" / "gambitpairing" / "resources" / "bin"
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / "bbpPairings.exe", destination / "bbpPairings.exe")
    shutil.copy2(source / "Apache-2.0.txt", destination / "BBP-Apache-2.0.txt")
    license_file = source / "LICENSE.txt"
    if sys.platform == "win32":
        # The Makefile's dist targets append the MinGW-w64 runtime (and, when
        # linked, winpthread) licenses that apply to a statically linked binary.
        subprocess.run(
            make_command(make, source, 1, "dist-targets", args.comp, args.static),
            check=True,
        )
        license_file = source / f"bbpPairings-{BBP_VERSION}" / "LICENSE.txt"
    shutil.copy2(license_file, destination / "BBP-LICENSE.txt")
    print(f"BBP {BBP_VERSION} staged in {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
