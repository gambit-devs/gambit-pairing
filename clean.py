#!/usr/bin/env python3

from pathlib import Path
import shutil
import sys

PROJECT_ROOT = Path(__file__).resolve().parent


def ensure_safe_root(root: Path) -> None:
    """Prevent accidental deletion outside project directory."""
    if not (root / "pyproject.toml").exists():
        print("Error: clean.py must be run on a python project root.")
        sys.exit(1)


def remove_path(path: Path) -> None:
    """Remove a file or directory safely."""
    try:
        if path.is_dir():
            shutil.rmtree(path)
            print(f"Removed directory: {path}")
        else:
            path.unlink(missing_ok=True)
            print(f"Removed file: {path}")
    except Exception as e:
        print(f"Failed to remove {path}: {e}")


def main() -> None:
    ensure_safe_root(PROJECT_ROOT)

    print(f"Cleaning project at: {PROJECT_ROOT}")
    print("-" * 40)

    # Build artifacts
    for folder in ["build", "dist"]:
        remove_path(PROJECT_ROOT / folder)

    # Egg metadata
    for egg_info in PROJECT_ROOT.glob("*.egg-info"):
        remove_path(egg_info)

    # Python bytecode
    for path in PROJECT_ROOT.rglob("__pycache__"):
        remove_path(path)

    for path in PROJECT_ROOT.rglob("*.py[co]"):
        remove_path(path)

    # Dev caches
    for cache in [".pytest_cache", ".mypy_cache"]:
        remove_path(PROJECT_ROOT / cache)

    print("-" * 40)
    print("Clean complete.")


if __name__ == "__main__":
    main()
