#!/usr/bin/env python3

import os
import shutil
from pathlib import Path


def clean_compiled_files(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_dir() and path.name == "__pycache__":
            shutil.rmtree(path)
            print(f"Removed dir: {path}")
        elif path.suffix == ".pyc":
            path.unlink()
            print(f"Removed file: {path}")


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
