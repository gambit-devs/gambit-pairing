#!/usr/bin/env python3

import os
from pathlib import Path
import subprocess
import sys


def main():
    try:

        # Set cwd for python process
        git_root = Path(__file__).parent.parent
        # Get the directory where this script is located
        script_dir = git_root / "scripts"

        # Run the ensure_all_dependencies.py script
        dependencies_script = script_dir / "ensure_all_dependencies.py"
        if dependencies_script.exists():
            print(f"Running dependencies script: {dependencies_script}")
            subprocess.run([sys.executable, str(dependencies_script)], check=True)
        else:
            print(f"Warning: Dependencies script not found: {dependencies_script}")

        # Install the package in editable mode

        # Set cwd for python process
        git_root = Path(__file__).parent.parent
        os.chdir(git_root)
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--editable", str(git_root)],
            check=True,
        )
        print("Python pip pkg installed in --editable mode")

        print(
            "Editable install complete. With this Python environment active, "
            "run 'gambit-pairing' from your shell."
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
