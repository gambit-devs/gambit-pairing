#!/usr/bin/env python3

import os
import shutil
from pathlib import Path


def clean_compiled_files(root: Path) -> None:
    # Remove __pycache__ directories
    for pycache_dir in root.rglob("__pycache__"):
        pycache_dir.unlink(missing_ok=True)

    # Remove stray .pyc files
    for pyc_file in root.rglob("*.pyc"):
        pyc_file.unlink()


def main():
    # Get the directory where this script is located
    script_dir = Path(__file__).parent

    print(f"cleaning: {script_dir}")

    # Define directories to clean
    built_dir = script_dir / "build"
    dist_dir = script_dir / "dist"
    src_dir = script_dir / "src"

    clean_compiled_files(src_dir)

    # Remove contents of directories if they exist
    for directory in [built_dir, dist_dir]:
        if directory.exists():
            # Remove all contents but keep the directory
            for item in directory.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                    print(f"Removed directory: {item}")
                else:
                    item.unlink()
                    print(f"Removed file: {item}")
        else:
            print(f"Directory not found (skipping): {directory}")

    print("cleaned out all built stuff")


if __name__ == "__main__":
    main()
