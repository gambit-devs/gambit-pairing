"""Tag wheels containing a staged native BBP engine as platform-specific.

Installs never compile the engine. Release builds stage it explicitly with
``python scripts/build_bbp.py`` before building; a wheel built without a staged
engine stays pure Python and the app reports the engine as unavailable.
"""

from pathlib import Path

from setuptools import setup

try:
    from setuptools.command.bdist_wheel import bdist_wheel
except ImportError:  # Compatibility with the declared setuptools>=61 floor.
    from wheel.bdist_wheel import bdist_wheel

ENGINE_DIR = Path(__file__).parent / "src" / "gambitpairing" / "resources" / "bin"


def engine_is_staged(engine_dir: Path = ENGINE_DIR) -> bool:
    return any(path.is_file() for path in engine_dir.glob("bbpPairings*"))


class EngineWheel(bdist_wheel):
    def finalize_options(self):
        super().finalize_options()
        if engine_is_staged():
            self.root_is_pure = False

    def get_tag(self):
        python, abi, platform = super().get_tag()
        if not engine_is_staged():
            return python, abi, platform
        # BBP is a subprocess: platform-dependent, but not Python-ABI-dependent.
        return "py3", "none", platform


setup(cmdclass={"bdist_wheel": EngineWheel})
