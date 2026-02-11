#!/usr/bin/env python3

import subprocess
import os
import sys
import tomllib
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"Running: {description}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error {description}: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr.strip()}")
        return False
    except FileNotFoundError:
        print(f"Command not found: {cmd[0]}")
        return False


def load_pyproject_dependencies():
    """Load dependencies from pyproject.toml."""
    try:
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)

        # Get main dependencies
        dependencies = data.get("project", {}).get("dependencies", [])

        # Get dev dependencies
        dev_dependencies = (
            data.get("project", {}).get("optional-dependencies", {}).get("dev", [])
        )

        return dependencies, dev_dependencies

    except FileNotFoundError:
        print("Error: pyproject.toml not found in current directory")
        return None, None
    except Exception as e:
        print(f"Error reading pyproject.toml: {e}")
        return None, None


def main():
    """Entry point."""
    # Set cwd for python process
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    # Ensure pip is up to date
    print("Ensuring pip is up to date")

    if not run_command(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip"], "updating pip"
    ):
        sys.exit(1)

    # Load dependencies from pyproject.toml
    dependencies, dev_dependencies = load_pyproject_dependencies()
    if dependencies is None:
        sys.exit(1)

    # Install main dependencies
    if dependencies:
        print("Installing dependencies (only if needed)")
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--upgrade-strategy",
            "only-if-needed",
        ] + dependencies
        if not run_command(cmd, "installing main dependencies"):
            sys.exit(1)
    else:
        print("No main dependencies found")

    # Install dev dependencies
    if dev_dependencies:
        print("Installing dev dependencies (only if needed)")
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--upgrade-strategy",
            "only-if-needed",
        ] + dev_dependencies
        if not run_command(cmd, "installing dev dependencies"):
            sys.exit(1)
    else:
        print("No dev dependencies found")

        # Set up pre-commit hooks
        print("Setting up pre-commit hooks")
        if not run_command(
            [sys.executable, "-m", "pre_commit", "install"], "setting up pre-commit"
        ):
            print(
                "Warning: pre-commit setup failed (this might be expected if pre-commit isn't installed)"
            )

        print("Dependencies setup completed successfully!")


if __name__ == "__main__":
    main()
