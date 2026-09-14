"""Tag wheels containing the staged native BBP engine as platform-specific."""

from pathlib import Path
import subprocess
import sys

from setuptools import setup
from setuptools.command.build_py import build_py

try:
    from setuptools.command.bdist_wheel import bdist_wheel
except ImportError:  # Compatibility with the declared setuptools>=61 floor.
    from wheel.bdist_wheel import bdist_wheel


class EngineBuild(build_py):
    def run(self):
        root = Path(__file__).parent
        if not (root / "src/gambitpairing/resources/bin/bbpPairings.exe").is_file():
            subprocess.run(
                [sys.executable, str(root / "scripts/build_bbp.py")], check=True
            )
        super().run()


class EngineWheel(bdist_wheel):
    def finalize_options(self):
        super().finalize_options()
        self.root_is_pure = False

    def get_tag(self):
        python, abi, platform = super().get_tag()
        # BBP is a subprocess: platform-dependent, but not Python-ABI-dependent.
        return "py3", "none", platform


setup(cmdclass={"bdist_wheel": EngineWheel, "build_py": EngineBuild})
