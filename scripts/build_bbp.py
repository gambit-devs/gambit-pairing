"""Build the pinned BBP source and stage the engine for application packaging.

Run inside a compiler-equipped environment (Fedora Toolbox on Kinoite).
No downloads, host package installation or compilation occurs at app startup.
"""

import argparse
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true", help="Run upstream C++ tests")
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    if not shutil.which("make") or not shutil.which("g++"):
        parser.error("make and g++ are required; on Kinoite run this script in Toolbox")
    root = Path(__file__).resolve().parents[1]
    source = root / "vendor" / "bbp"
    subprocess.run(
        [
            "make",
            "-C",
            str(source),
            f"-j{args.jobs}",
            "version=v6.0.0",
            "test" if args.test else "all",
        ],
        check=True,
    )
    destination = root / "src" / "gambitpairing" / "resources" / "bin"
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / "bbpPairings.exe", destination / "bbpPairings.exe")
    for name in ("LICENSE.txt", "Apache-2.0.txt"):
        shutil.copy2(source / name, destination / f"BBP-{name}")
    print(f"BBP v6.0.0 staged in {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
