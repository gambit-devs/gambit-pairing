"""Release packaging: engine staging, Breeze bundling and the frozen runtime."""

import hashlib
import importlib.util
import io
import os
from pathlib import Path
import re
import sys
from types import SimpleNamespace
from typing import Any, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from gambitpairing import __main__ as entry

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
LICENSES = ROOT / "licenses" / "breeze"


def _load(name):
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stage_breeze = _load("stage_breeze")
build_bbp = _load("build_bbp")
pyinstaller_common = _load("pyinstaller_common")
make_executable = _load("make_executable")


# -- frozen runtime -----------------------------------------------------------


def test_bundled_plugin_dir_matches_pyinstaller_layout():
    assert entry.BUNDLED_QT_PLUGIN_DIR == pyinstaller_common.BUNDLED_QT_PLUGIN_DIR


def test_bundled_plugin_dir_only_for_frozen_builds(monkeypatch, tmp_path):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert entry.bundled_qt_plugin_dir() is None

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert entry.bundled_qt_plugin_dir() == tmp_path / "qt_plugins"


def test_frozen_build_adds_its_plugin_dir(monkeypatch, tmp_path):
    (tmp_path / "qt_plugins" / "styles").mkdir(parents=True)
    added = []
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(entry.QCoreApplication, "addLibraryPath", added.append)

    entry.add_bundled_qt_plugin_path()

    assert added == [str(tmp_path / "qt_plugins")]


def test_frozen_build_ignores_host_breeze(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "linux")
    added = []
    monkeypatch.setattr(entry.QCoreApplication, "addLibraryPath", added.append)

    entry.add_host_breeze_plugin_paths(cast(Any, SimpleNamespace(libraryPaths=list)))

    assert added == []


def test_verify_native_style_is_strict_only_when_frozen(monkeypatch):
    from PyQt6 import QtWidgets

    app = cast(
        QtWidgets.QApplication,
        QtWidgets.QApplication.instance() or QtWidgets.QApplication([]),
    )
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert entry.verify_native_style(app, "Fusion") == 0
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert entry.verify_native_style(app, "Fusion") == 1
    assert entry.verify_native_style(app, "Breeze") == 0


def test_velopack_hooks_run_first_only_in_frozen_builds(monkeypatch):
    calls = []

    class FakeApp:
        def set_auto_apply_on_startup(self, value):
            calls.append(("auto_apply", value))
            return self

        def run(self):
            calls.append("run")

    monkeypatch.setitem(sys.modules, "velopack", SimpleNamespace(App=FakeApp))
    monkeypatch.delattr(sys, "frozen", raising=False)
    entry.run_velopack_hooks()
    assert calls == []

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    entry.run_velopack_hooks()
    assert calls == [("auto_apply", True), "run"]


def test_main_runs_velopack_before_the_app(monkeypatch):
    order = []
    monkeypatch.setattr(entry, "run_velopack_hooks", lambda: order.append("velopack"))
    monkeypatch.setattr(entry, "run_app", lambda: order.append("app") or 0)
    with pytest.raises(SystemExit):
        entry.main()
    assert order == ["velopack", "app"]


# -- Breeze staging -------------------------------------------------------------


@pytest.mark.parametrize(
    ("system", "machine", "target"),
    [
        ("linux", "x86_64", "linux-x86_64"),
        ("win32", "AMD64", "windows-x86_64"),
        ("darwin", "arm64", "macos-arm64"),
        ("darwin", "x86_64", "macos-x86_64"),
    ],
)
def test_current_target(system, machine, target):
    assert stage_breeze.current_target(system, machine) == target


def test_pins_are_complete_and_consistent():
    pins = stage_breeze.load_pins()
    assert set(pins["targets"]) == {
        "linux-x86_64",
        "windows-x86_64",
        "macos-arm64",
        "macos-x86_64",
    }
    sha256 = re.compile(r"[0-9a-f]{64}")
    for target, spec in pins["targets"].items():
        names = {package["name"] for package in spec["packages"]}
        built = spec.get("rebuild", {}).get("frameworks", [])
        assert spec["plugin"]["package"] == "kde/plasma/breeze" in names
        for library in spec["libraries"]:
            assert library.get("package") in names or library.get("framework") in built
        build_only = spec.get("rebuild", {}).get("build_packages", [])
        for package in spec["packages"] + build_only:
            assert sha256.fullmatch(package["sha256"]), package
            assert package["file"].startswith(package["name"] + "/"), package
            assert package["license"] and package["source"]
            assert any((LICENSES / package["license_dir"]).glob("*")), package


def test_windows_and_macos_rebuild_the_zstd_frameworks():
    pins = stage_breeze.load_pins()
    sources = pins["framework_sources"]
    sdks = pins["qt_sdks"]
    assert re.fullmatch(r"6\.\d+\.\d+", sdks["version"])
    rebuilt = {"breeze-icons", "kcolorscheme", "kiconthemes"}
    # Linux keeps using KDE Craft's binaries unchanged.
    assert "rebuild" not in pins["targets"]["linux-x86_64"]
    for target in ("windows-x86_64", "macos-arm64", "macos-x86_64"):
        spec = pins["targets"][target]
        rebuild = spec["rebuild"]
        assert rebuild["frameworks"][0] == "extra-cmake-modules"
        assert rebuilt <= set(rebuild["frameworks"])
        assert not {p["name"].rsplit("/", 1)[1] for p in spec["packages"]} & rebuilt
        from_source = {
            lib["framework"] for lib in spec["libraries"] if "framework" in lib
        }
        assert from_source == rebuilt
        for archive in sdks["sdks"][rebuild["qt_sdk"]]["archives"]:
            assert re.fullmatch(r"[0-9a-f]{64}", archive["sha256"]), archive
            assert sdks["version"] in archive["file"]
    for name, source in sources.items():
        if name.startswith("_"):
            continue
        assert re.fullmatch(r"[0-9a-f]{64}", source["sha256"]), name
        assert source["url"].startswith("https://download.kde.org/stable/")
        assert Path(source["url"]).name.startswith(source["directory"])
        for patch in source.get("patches", []):
            assert re.fullmatch(r"[0-9a-f]{64}", patch["sha256"]), patch
        if name in rebuilt:
            assert any((LICENSES / source["license_dir"]).glob("*")), name


def test_download_verifies_checksum(tmp_path):
    payload = b"archive bytes"
    good = hashlib.sha256(payload).hexdigest()

    def opener(url):
        return io.BytesIO(payload)

    path = stage_breeze.download("https://x.test/a.7z", tmp_path / "a.7z", good, opener)
    assert path.read_bytes() == payload
    with pytest.raises(stage_breeze.StageError):
        stage_breeze.download(
            "https://x.test/b.7z", tmp_path / "b.7z", "0" * 64, opener
        )
    assert not (tmp_path / "b.7z").exists()


def test_zstd_resources_need_a_zstd_qt(tmp_path):
    kf6 = tmp_path / "KF6IconThemes.dll"
    kf6.write_bytes(b"...?qResourceFeatureZstd@@YAEXZ...")
    qt_without = tmp_path / "Qt6Core.dll"
    qt_without.write_bytes(b"?qResourceFeatureZlib@@YAEXZ")
    with pytest.raises(stage_breeze.StageError, match="zstd"):
        stage_breeze.check_qt_compatibility([kf6], qt_without)

    qt_with = tmp_path / "QtCore"
    qt_with.write_bytes(b"_qt_resourceFeatureZstd")
    stage_breeze.check_qt_compatibility([kf6], qt_with)
    with pytest.raises(stage_breeze.StageError):
        stage_breeze.check_qt_compatibility([kf6], None)


def test_sevenzip_link_switch_only_for_7zip_25_and_later():
    banners = {
        "7-Zip 26.04 (x64) : Copyright (c) 1999-2026 Igor Pavlov": ["-snld20"],
        "7-Zip (z) 25.01 (arm64) : Copyright (c) 1999-2025 Igor Pavlov": ["-snld20"],
        "7-Zip 24.08 (x64) : Copyright (c) 1999-2024 Igor Pavlov": [],
        "7-Zip [64] 16.02 : Copyright (c) 1999-2016 Igor Pavlov : p7zip": [],
    }
    for banner, expected in banners.items():
        assert stage_breeze.sevenzip_link_args("7z", banner) == expected, banner


def test_sdk_version_must_match_the_wheel():
    stage_breeze.check_sdk_matches_wheel("6.11.2", "6.11.2")
    for wheel in ("6.11.3", "6.12.0", None):
        with pytest.raises(stage_breeze.StageError, match="PyQt6-Qt6==6.11.2"):
            stage_breeze.check_sdk_matches_wheel("6.11.2", wheel)


def test_framework_build_rejects_host_packages(tmp_path):
    pinned = [tmp_path / "prefix", tmp_path / "qt", tmp_path / "craft"]
    cache = tmp_path / "CMakeCache.txt"
    cache.write_text(
        f"ECM_DIR:PATH={pinned[0]}/share/ECM/cmake\n"
        f"Qt6Gui_DIR:PATH={pinned[1]}/lib/cmake/Qt6Gui\n"
        f"KF6Config_DIR:PATH={pinned[2]}/lib/cmake/KF6Config\n"
        "Qt6Tools_DIR:PATH=Qt6Tools_DIR-NOTFOUND\n"
        "ZLIB_DIR:PATH=/usr/lib64/cmake/zlib\n"
    )
    stage_breeze.check_resolved_packages(cache, pinned)
    with cache.open("a") as handle:
        handle.write("KF6I18n_DIR:PATH=/usr/lib64/cmake/KF6I18n\n")
    with pytest.raises(stage_breeze.StageError, match="KF6I18n"):
        stage_breeze.check_resolved_packages(cache, pinned)


def test_cmake_command_uses_pinned_prefixes(tmp_path):
    tools = {"cmake": "cmake", "ninja": "ninja", "msgfmt": "f", "msgmerge": "m"}
    framework = {"cmake_args": ["-DUSE_DBUS=OFF"]}
    command = stage_breeze.cmake_command(
        framework,
        tmp_path / "src",
        tmp_path / "b",
        tmp_path / "p",
        [tmp_path / "p", tmp_path / "qt"],
        ["-DCMAKE_OSX_ARCHITECTURES=arm64"],
        tools,
    )
    assert command[:2] == ["cmake", "-S"]
    assert ["-G", "Ninja"] == command[command.index("-G") : command.index("-G") + 2]
    prefix_path = next(arg for arg in command if arg.startswith("-DCMAKE_PREFIX_PATH="))
    assert prefix_path.endswith(
        f"{(tmp_path / 'p').as_posix()};{(tmp_path / 'qt').as_posix()}"
    )
    assert command[-2:] == ["-DUSE_DBUS=OFF", "-DCMAKE_OSX_ARCHITECTURES=arm64"]


def test_notice_and_licenses_cover_shipped_components(tmp_path):
    pins = stage_breeze.load_pins()
    spec = pins["targets"]["windows-x86_64"]
    components = stage_breeze.shipped_components(pins, spec)
    names = {item["name"] for item in components}
    assert {"breeze-icons", "kcolorscheme", "kiconthemes", "kde/plasma/breeze"} <= names
    assert "extra-cmake-modules" not in names
    assert "kde/frameworks/tier1/kwidgetsaddons" not in names  # build only
    copied = stage_breeze.copy_licenses(tmp_path, components, LICENSES)
    assert "licenses/win-iconv/readme.txt" in copied
    assert "licenses/breeze-icons/GPL-3.0.txt" in copied
    assert all((tmp_path / path).is_file() for path in copied)
    stage_breeze.write_notice(tmp_path, "windows-x86_64", pins, components)
    notice = (tmp_path / stage_breeze.NOTICE_NAME).read_text()
    assert "kiconthemes 6.31.0 (source)" in notice
    assert "official Qt 6.11.2 SDK" in notice
    assert "breeze-icons-6.23.0-symlink-fix.diff" in notice


def test_stage_takes_rebuilt_frameworks_from_the_source_build(tmp_path, monkeypatch):
    pins = stage_breeze.load_pins()
    spec = pins["targets"]["windows-x86_64"]
    downloads = []

    def fake_download(url, destination, expected_sha256, opener=None):
        downloads.append(url)
        return destination

    def fake_extract(archive, destination, sevenzip):
        for package in spec["packages"] + spec["rebuild"]["build_packages"]:
            if Path(package["file"]).name == archive.name:
                members = [spec["plugin"]] + spec["libraries"]
                for member in members:
                    if member.get("package") == package["name"]:
                        path = destination / member["member"]
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_bytes(b"craft")

    def fake_build(pins_, spec_, unpacked, work_dir, cache_dir, sevenzip, opener):
        assert "kde/frameworks/tier1/kwidgetsaddons" in unpacked
        prefix = work_dir / "p"
        for library in spec_["libraries"]:
            if "framework" in library:
                path = prefix / library["member"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"source")
        return prefix

    monkeypatch.setattr(stage_breeze, "download", fake_download)
    monkeypatch.setattr(stage_breeze, "extract", fake_extract)
    monkeypatch.setattr(stage_breeze, "find_7z", lambda: "7z")
    monkeypatch.setattr(stage_breeze, "build_frameworks", fake_build)
    stage_dir = stage_breeze.stage(
        "windows-x86_64",
        tmp_path / "dest",
        tmp_path / "cache",
        pins=pins,
        skip_compat_check=True,
    )
    lib = stage_dir / "lib"
    assert (lib / "KF6IconThemes.dll").read_bytes() == b"source"
    assert (lib / "KF6ConfigCore.dll").read_bytes() == b"craft"
    assert not (lib / "KF6WidgetsAddons.dll").exists()
    assert not any("kiconthemes-6.31.0-153" in url for url in downloads)
    manifest = (stage_dir / stage_breeze.STAGE_MANIFEST).read_text()
    assert "licenses/kiconthemes/" in manifest


# -- engine and build preconditions ----------------------------------------------


def test_build_bbp_command_options():
    command = build_bbp.make_command("make", Path("src"), 4, "all", "gcc", True)
    assert command[-1] == "all"
    assert {"-j4", "version=v6.0.0", "COMP=gcc", "static=yes"} <= set(command)
    assert "static=yes" not in build_bbp.make_command(
        "make", Path("s"), 1, "all", "clang", False
    )
    assert build_bbp.default_comp("darwin") == "clang"
    assert build_bbp.default_comp("linux") == "gcc"


def test_setup_py_never_builds_the_engine():
    text = (ROOT / "setup.py").read_text()
    assert "build_py" not in text and "import subprocess" not in text


def test_make_executable_requires_staged_engine_and_breeze(monkeypatch):
    monkeypatch.setattr(pyinstaller_common, "BBP_BINARIES", [])
    monkeypatch.setattr(pyinstaller_common, "BREEZE_BINARIES", [("x", "y")])
    monkeypatch.setattr(make_executable, "pyinstaller_common", pyinstaller_common)
    with pytest.raises(make_executable.BuildError, match="BBP"):
        make_executable.check_staged_components()

    monkeypatch.setattr(pyinstaller_common, "BBP_BINARIES", [Path("bbpPairings.exe")])
    monkeypatch.setattr(pyinstaller_common, "BREEZE_BINARIES", [])
    with pytest.raises(make_executable.BuildError, match="Breeze"):
        make_executable.check_staged_components()
    assert "--allow-missing-breeze" not in (SCRIPTS / "make_executable.py").read_text()


def test_verify_bundle_checks_engine_and_breeze(tmp_path, monkeypatch):
    monkeypatch.setattr(make_executable, "pyinstaller_common", pyinstaller_common)
    exe = make_executable.expected_executable(tmp_path)
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    with pytest.raises(make_executable.BuildError, match="engine"):
        make_executable.verify_bundle(tmp_path)
    engine_dir = exe.parent / "_internal" / "gambitpairing" / "resources" / "bin"
    engine_dir.mkdir(parents=True)
    (engine_dir / "bbpPairings.exe").write_bytes(b"")
    with pytest.raises(make_executable.BuildError, match="Breeze"):
        make_executable.verify_bundle(tmp_path)
    styles = exe.parent / "_internal" / "qt_plugins" / "styles"
    styles.mkdir(parents=True)
    (styles / "breeze6.so").write_bytes(b"")
    with pytest.raises(make_executable.BuildError, match="license"):
        make_executable.verify_bundle(tmp_path)
    texts = exe.parent / "_internal" / "qt_plugins" / "licenses" / "kconfig"
    texts.mkdir(parents=True)
    (texts / "LGPL-2.0-or-later.txt").write_text("text")
    with pytest.raises(make_executable.BuildError, match="Licence texts"):
        make_executable.verify_bundle(tmp_path)
    internal = exe.parent / "_internal"
    licence_dir = internal / pyinstaller_common.THIRD_PARTY_BUNDLE_DIR
    for path in (
        internal / "pyqt6_qt6-6.11.2.dist-info" / "LICENSE",
        licence_dir / "python" / "LICENSE.txt",
        licence_dir / "velopack" / "LICENSE",
        licence_dir / "gcc-runtime" / "COPYING.RUNTIME",
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("text")
    make_executable.verify_bundle(tmp_path)
