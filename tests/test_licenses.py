"""Tests for the runtime closure and the bundle licence checks."""

from importlib import metadata
import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def _load(name: str) -> ModuleType:
    """Load a scripts/ module by path, registered so sibling imports share it."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


pyinstaller_common = _load("pyinstaller_common")
make_executable = _load("make_executable")


class FakeDist:
    def __init__(self, root, requires=()):
        self.root = Path(root)
        self.requires = list(requires)


def write(path: Path, text: str = "licence text\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_optional_extras_are_not_runtime_requirements():
    from packaging.requirements import Requirement

    assert not pyinstaller_common.requirement_applies(
        Requirement("click==8.*; extra == 'cli'")
    )
    assert pyinstaller_common.requirement_applies(Requirement("httpx>=0.28"))
    platform_gated = Requirement("colorama; sys_platform == 'win32'")
    assert pyinstaller_common.requirement_applies(platform_gated) is (
        sys.platform == "win32"
    )


def test_runtime_distributions_follow_requirements_and_skip_extras(monkeypatch):
    dists = {
        "gambit-pairing": FakeDist(
            "/x", requires=["httpx>=0.28", "click; extra == 'cli'"]
        ),
        "httpx": FakeDist("/x", requires=["anyio"]),
        "anyio": FakeDist("/x"),
    }

    def fake_distribution(name):
        try:
            return dists[name]
        except KeyError:
            raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(pyinstaller_common.metadata, "distribution", fake_distribution)
    closure = pyinstaller_common.runtime_distributions("gambit-pairing")
    assert set(closure) == {"gambit-pairing", "httpx", "anyio"}


def test_runtime_distributions_require_the_project_installed(monkeypatch):
    def missing(name):
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(pyinstaller_common.metadata, "distribution", missing)
    with pytest.raises(RuntimeError, match="install the project"):
        pyinstaller_common.runtime_distributions("gambit-pairing")


def test_licence_check_reports_missing_texts(tmp_path):
    with pytest.raises(make_executable.BuildError, match="Licence texts are missing"):
        make_executable.check_licence_texts(tmp_path)


def test_licence_check_accepts_complete_texts(tmp_path, monkeypatch):
    internal = tmp_path / "_internal"
    write(internal / "pyqt6_qt6-6.11.2.dist-info" / "LICENSE")
    licence_dir = internal / pyinstaller_common.THIRD_PARTY_BUNDLE_DIR
    write(licence_dir / "python" / "LICENSE.txt")
    write(licence_dir / "velopack" / "LICENSE")
    write(licence_dir / "gcc-runtime" / "COPYING.RUNTIME")
    make_executable.check_licence_texts(internal)


def test_licence_check_needs_the_qt_licence_from_its_dist_info(tmp_path):
    internal = tmp_path / "_internal"
    licence_dir = internal / pyinstaller_common.THIRD_PARTY_BUNDLE_DIR
    write(licence_dir / "python" / "LICENSE.txt")
    write(licence_dir / "velopack" / "LICENSE")
    write(licence_dir / "gcc-runtime" / "COPYING.RUNTIME")
    with pytest.raises(make_executable.BuildError, match="pyqt6_qt6"):
        make_executable.check_licence_texts(internal)


def test_bundle_check_refuses_undeclared_distributions(tmp_path, monkeypatch):
    internal = tmp_path / "_internal"
    write(
        internal / "pluggy-1.7.0.dist-info" / "METADATA",
        "Metadata-Version: 2.1\nName: pluggy\nVersion: 1.7.0\n",
    )
    write(
        internal / "anyio-4.15.1.dist-info" / "METADATA",
        "Metadata-Version: 2.1\nName: anyio\nVersion: 4.15.1\n",
    )
    monkeypatch.setattr(
        pyinstaller_common,
        "RUNTIME_DISTRIBUTIONS",
        {"anyio": FakeDist(tmp_path), "gambit-pairing": FakeDist(tmp_path)},
    )
    with pytest.raises(make_executable.BuildError, match="pluggy"):
        make_executable.check_bundled_distributions(internal)


def test_bundle_check_accepts_declared_distributions(tmp_path, monkeypatch):
    internal = tmp_path / "_internal"
    write(
        internal / "anyio-4.15.1.dist-info" / "METADATA",
        "Metadata-Version: 2.1\nName: anyio\nVersion: 4.15.1\n",
    )
    monkeypatch.setattr(
        pyinstaller_common,
        "RUNTIME_DISTRIBUTIONS",
        {"anyio": FakeDist(tmp_path), "gambit-pairing": FakeDist(tmp_path)},
    )
    make_executable.check_bundled_distributions(internal)
