#!/usr/bin/env python3
import argparse
import importlib.util
import subprocess
import sys
import tomllib


def run_command(cmd, description, check_mode=False):
    """Run a command and handle errors"""
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
    """Load dependencies from pyproject.toml"""
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
    parser = argparse.ArgumentParser(
        description="Format Python code using black and isort"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Don't write changes, just check if formatting is needed",
    )
    args = parser.parse_args()

    check_mode = args.check

    # Ensure pip is up to date
    print("Ensuring pip is up to date")
    if not run_command(
        [sys.executable, "-m", "ensurepip", "--upgrade"], "updating pip"
    ):
        sys.exit(1)

    black = importlib.util.find_spec("black")
    isort = importlib.util.find_spec("isort")
    if not black or not isort:
        # Load dependencies from pyproject.toml
        dependencies, dev_dependencies = load_pyproject_dependencies()
        if dependencies is None:
            sys.exit(1)

        # Install main dependencies
        if dependencies:
            print("Installing dependencies")
            cmd = [sys.executable, "-m", "pip", "install"] + dependencies
            if not run_command(cmd, "installing main dependencies"):
                sys.exit(1)
        else:
            print("No main dependencies found")

        # Install dev dependencies
        if dev_dependencies:
            print("Installing dev dependencies")
            cmd = [sys.executable, "-m", "pip", "install"] + dev_dependencies
            if not run_command(cmd, "installing dev dependencies"):
                sys.exit(1)
        else:
            print("No dev dependencies found")

    # Prepare commands based on check mode
    isort_cmd = [sys.executable, "-m", "isort"]
    black_cmd = [sys.executable, "-m", "black"]

    if check_mode:
        isort_cmd.append("--check-only")
        black_cmd.append("--check")

    isort_cmd.append("src")
    black_cmd.append("src")

    success = True

    if not run_command(isort_cmd, "Checking/formatting with isort", check_mode):
        print(
            "isort check failed. Code formatting required."
            if check_mode
            else "isort failed. Ensure current working dir is git root"
        )
        success = False
    else:
        print(
            "------- isort check passed ----------"
            if check_mode
            else "------- isort ran ----------"
        )

    if not run_command(black_cmd, "Checking/formatting with black", check_mode):
        print(
            "black check failed. Code formatting required."
            if check_mode
            else "black failed. Ensure current working dir is git root"
        )
        success = False
    else:
        print(
            "------- black check passed ----------"
            if check_mode
            else "------- black ran ----------"
        )

    if success:
        print(
            "----- src format check passed --------"
            if check_mode
            else "----- src formatted --------"
        )
        if not check_mode:
            print("--- Hint: ensure new formatted files are added to any commit. ---")
    else:
        if check_mode:
            print(
                "Format check failed. Run 'python format_project.py' to fix formatting issues."
            )
        sys.exit(1)


if __name__ == "__main__":
    main()
