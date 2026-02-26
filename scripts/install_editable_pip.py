#!/usr/bin/env python3

import os
import subprocess
import sys
from pathlib import Path


def main():
    try:
        # Get the directory where this script is located
        script_dir = Path(__file__).parent

        # Run the ensure_all_dependencies.py script
        dependencies_script = script_dir / "ensure_all_dependencies.py"
        if dependencies_script.exists():
            print(f"Running dependencies script: {dependencies_script}")
            subprocess.run([sys.executable, str(dependencies_script)], check=True)
        else:
            print(f"Warning: Dependencies script not found: {dependencies_script}")

        print("Python pip pkg installed in --editable mode")

        # Install the package in editable mode
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--editable", str(script_dir)],
            check=True,
        )

        print(
            "now gambit-pairing should be on your $PATH, try gambit-paining in your shell"
        )

    except subprocess.CalledProcessError as e:
        print(
            "FAIL: Make sure you have installed pip requirements, and activated any relevant venvs"
        )
        sys.exit(1)
    except Exception as e:
        print(
            f"FAIL: Make sure you have installed pip requirements, and activated any relevant venvs"
        )
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
