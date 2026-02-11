#!/usr/bin/env python3
"""
Executable creation script for Gambit Pairing using PyInstaller.

Creates single-file or single-directory executables from the Python source.

Usage:
  python make_executable.py                     # Build single-file executable (default)
  python make_executable.py --onefile          # Build single-file executable (explicit)
  python make_executable.py --onedir           # Build single-directory executable
  python make_executable.py --spec <path>      # Use custom spec file

The onedir build is required for MSI creation, while onefile is more portable.
"""

import argparse
import subprocess
import os
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command with error handling."""
    print(f"Running: {description}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout.strip():
            print(f"Output: {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        if e.stdout.strip():
            print(f"stdout: {e.stdout.strip()}")
        if e.stderr.strip():
            print(f"stderr: {e.stderr.strip()}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"Command not found: {cmd[0]}")
        print("Make sure it's installed and in your PATH")
        sys.exit(1)


def ensure_dependencies():
    """Ensure all dependencies are installed."""
    script_dir = Path(__file__).parent
    dependency_script = script_dir / "ensure_all_dependencies.py"

    if dependency_script.exists():
        print("Ensuring dependencies are installed...")
        run_command([sys.executable, str(dependency_script)], "Installing dependencies")
    else:
        print(
            "Warning: ensure_all_dependencies.py not found, skipping dependency check"
        )


def build_executable(spec_file: Path):
    """Build executable using PyInstaller."""
    if not spec_file.exists():
        print(f"Error: Spec file not found: {spec_file}")
        sys.exit(1)

    print(f"Building executable with: {spec_file.name}")
    run_command(
        ["pyinstaller", "--clean", "-y", str(spec_file)],
        f"PyInstaller ({spec_file.name})",
    )

    name = "gambit-pairing"
    # Verify the build
    if spec_file.name.endswith("-onedir.spec"):
        expected_exe = Path("dist") / (
            name + (".exe" if sys.platform == "win32" else "")
        )
        build_type = "onedir"
    else:
        expected_exe = Path("dist") / (
            name + (".exe" if sys.platform == "win32" else "")
        )
        build_type = "onefile"

    if expected_exe.exists():
        size_mb = expected_exe.stat().st_size / (1024 * 1024)
        print(
            f"[+] {build_type.capitalize()} executable created: {expected_exe} ({size_mb:.1f} MB)"
        )
    else:
        print(f"[x] Error: Expected executable not found: {expected_exe}")
        sys.exit(1)


def main():
    """Entry point."""
    script_dir = Path(__file__).parent
    os.chdir(script_dir)  # set script cwd

    parser = argparse.ArgumentParser(
        description="Build Gambit Pairing executable using PyInstaller",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Build Types:
  --onefile   Creates a single executable file (portable, slower startup)
  --onedir    Creates a directory with executable and dependencies (faster startup, required for MSI)

Examples:
  python make_executable.py              # Build single-file executable
  python make_executable.py --onedir     # Build directory-based executable for MSI creation
        """,
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--onedir",
        action="store_true",
        help="Build a single-directory (onedir) executable (required for MSI)",
    )
    group.add_argument(
        "--onefile",
        action="store_true",
        help="Build a single-file (onefile) executable (default, portable)",
    )
    parser.add_argument("--spec", help="Override spec filename to use (path)")
    parser.add_argument(
        "--skip-deps", action="store_true", help="Skip dependency installation check"
    )

    args = parser.parse_args()

    print("Gambit Pairing - Executable Builder")
    print("=" * 40)

    # Install dependencies unless skipped
    if not args.skip_deps:
        ensure_dependencies()

    # Choose spec file
    if args.spec:
        spec_file = Path(args.spec)
    elif args.onedir:
        spec_file = script_dir / "gambit-pairing-onedir.spec"
    else:
        # Default to onefile (more portable)
        spec_file = script_dir / "gambit-pairing.spec"

    # Build the executable
    build_executable(spec_file)

    print(f"\nBuild completed successfully!")


if __name__ == "__main__":
    main()

#  LocalWords:  onefile onedir MSI
