#!/usr/bin/env python3
"""build gambit-pairing ui."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
UI_DIR = ROOT / "src" / "gambitpairing" / "ui"
OUT_DIR = ROOT / "src" / "gambitpairing" / "ui_gen"


def main() -> int:
    """Entry-point and doer."""
    if not UI_DIR.exists():
        print(f"UI directory not found: {UI_DIR}")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Ensure ui_gen is a package
    (OUT_DIR / "__init__.py").touch(exist_ok=True)

    ui_files = list(UI_DIR.glob("*.ui"))
    if not ui_files:
        print("No .ui files found.")
        return 0

    for ui_file in ui_files:
        out_file = OUT_DIR / f"ui_{ui_file.stem}.py"
        print(f"Generating {out_file.name}")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "PyQt6.uic.pyuic",
                str(ui_file),
                "-o",
                str(out_file),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(result.stderr.strip())
            return result.returncode

    print("UI generation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
