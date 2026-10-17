#!/usr/bin/env python3
"""Stage the KDE Breeze Qt6 widget style for a PyInstaller release build.

The Breeze style plugin and most KDE Frameworks libraries it needs come from
KDE Craft's prebuilt binary cache. ``scripts/breeze_craft_pins.json`` pins every
archive by file name and SHA-256, so a build downloads exactly those bytes.

On Windows and macOS, three of Craft's frameworks (``breeze-icons``,
``kcolorscheme`` and ``kiconthemes``) cannot be used as they are: their Qt
resources are zstd-compressed, which the PyQt6-Qt6 wheel's Qt Core does not
support. For those targets the pins name a ``rebuild`` section, and this script
builds the three frameworks (and ECM, which they need to configure) from pinned
KDE source tarballs against the official Qt SDK of the same version as the
wheel, downloaded from download.qt.io and pinned by SHA-256. The other Craft
binaries are reused as they are.

The staged tree is ``build/breeze/<target>/``::

    plugins/styles/breeze6.<ext>   Qt style plugin
    lib/                           KF6 and helper libraries (by soname/DLL name)
    licenses/                      full license texts for everything staged
    BREEZE-NOTICE.txt              package, version, source and license list
    stage.json                     what was staged, for the PyInstaller spec

``scripts/pyinstaller_common.py`` collects this tree, and the frozen app adds
the bundled plugin directory to Qt's library paths at startup.

Before staging, the script checks the plugin can link against the Qt runtime
that PyInstaller will bundle (the PyQt6-Qt6 wheel). It fails with an
explanation instead of producing a build that silently falls back to another
style.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
PINS_FILE = Path(__file__).resolve().parent / "breeze_craft_pins.json"
LICENSE_DIR = ROOT / "licenses" / "breeze"
DEFAULT_DEST = ROOT / "build" / "breeze"
DEFAULT_CACHE = ROOT / "build" / "breeze-cache"
NOTICE_NAME = "BREEZE-NOTICE.txt"
STAGE_MANIFEST = "stage.json"
STAGED_LICENSE_DIR = "licenses"

# Bump when the framework build recipe changes in a way the pins do not show,
# so a cached build is not reused.
RECIPE_VERSION = 1

# Qt's rcc emits a reference to a Qt Core feature symbol when it compresses
# resources with zstd (qResourceFeatureZstd on Windows, qt_resourceFeatureZstd
# on macOS). A library built that way cannot load into a Qt Core built without
# zstd, which is the case for the PyQt6-Qt6 wheels on Windows and macOS.
ZSTD_RESOURCE_MARKER = b"esourceFeatureZstd"

# CMake package directories a framework build may resolve; each must come from
# the pinned inputs, never from the build machine.
PINNED_PACKAGE_DIR = re.compile(r"^((?:KF6|Qt6|ECM)\w*)_DIR:PATH=(.+)$")


class StageError(Exception):
    """A fatal staging problem with a message for the user."""


def current_target(system: str | None = None, machine: str | None = None) -> str:
    """Return the pins target name for this machine."""
    system = system or sys.platform
    machine = (machine or platform.machine()).lower()
    arch = {"amd64": "x86_64", "x86_64": "x86_64", "arm64": "arm64"}.get(machine)
    arch = arch or {"aarch64": "arm64"}.get(machine, machine)
    if system.startswith("linux"):
        os_name = "linux"
    elif system == "win32":
        os_name = "windows"
    elif system == "darwin":
        os_name = "macos"
    else:
        raise StageError(f"Unsupported platform for Breeze staging: {system}")
    return f"{os_name}-{arch}"


def load_pins(path: Path = PINS_FILE) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def target_pins(pins: dict, target: str) -> dict:
    try:
        return pins["targets"][target]
    except KeyError:
        known = ", ".join(sorted(pins["targets"]))
        raise StageError(
            f"No pinned Breeze packages for {target}. Known targets: {known}"
        ) from None


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, destination: Path, expected_sha256: str, opener=None) -> Path:
    """Download ``url`` to ``destination`` unless a verified copy is cached."""
    if destination.is_file() and sha256_of(destination) == expected_sha256:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    opener = opener or urllib.request.urlopen
    print(f"Downloading {url}", flush=True)
    with opener(url) as response, open(partial, "wb") as handle:
        shutil.copyfileobj(response, handle)
    actual = sha256_of(partial)
    if actual != expected_sha256:
        partial.unlink(missing_ok=True)
        raise StageError(
            f"Checksum mismatch for {url}\n  expected {expected_sha256}\n  got      {actual}"
        )
    partial.replace(destination)
    return destination


def find_7z() -> str:
    for name in ("7z", "7zz", "7za"):
        found = shutil.which(name)
        if found:
            return found
    raise StageError("7-Zip (7z, 7zz or 7za) is required to unpack KDE Craft archives.")


def extract(archive: Path, destination: Path, sevenzip: str) -> None:
    """Extract a ``.7z``, ``.tar.7z`` or ``.tar.xz`` archive into ``destination``."""
    destination.mkdir(parents=True, exist_ok=True)
    if archive.name.endswith(".tar.7z"):
        result = subprocess.run(
            [sevenzip, "x", "-so", str(archive)], capture_output=True, check=True
        )
        with tarfile.open(fileobj=io.BytesIO(result.stdout)) as tar:
            tar.extractall(destination, filter="data")
    elif archive.name.endswith(".tar.xz"):
        # Where symlinks cannot be created (Windows without the privilege),
        # tarfile copies the link target instead.
        with tarfile.open(archive) as tar:
            tar.extractall(destination, filter="data")
    else:
        subprocess.run(
            [sevenzip, "x", "-y", *sevenzip_link_args(sevenzip)]
            + [f"-o{destination}", str(archive)],
            capture_output=True,
            check=True,
        )


def sevenzip_link_args(sevenzip: str, banner: str | None = None) -> list[str]:
    """Let 7-Zip 25+ restore the Qt SDK's library symlinks.

    7-Zip 25 skips a symlink that points at another symlink (``libQt6DBus.so ->
    libQt6DBus.so.6 -> libQt6DBus.so.6.11.2``) unless ``-snld20`` is given;
    older 7-Zip and p7zip reject that switch. Every archive this script
    unpacks is pinned by SHA-256.
    """
    if banner is None:
        banner = subprocess.run([sevenzip], capture_output=True, text=True).stdout
    match = re.search(r"7-Zip(?: \(\w\))?(?: \[\d+\])? (\d+)\.\d+", banner)
    return ["-snld20"] if match and int(match.group(1)) >= 25 else []


def resolve_member(root: Path, member: str) -> Path:
    """Return the real file behind an archive member, following symlinks."""
    path = root / member
    if not path.exists():
        raise StageError(f"{member} is missing from {root}")
    resolved = path.resolve()
    if root.resolve() not in resolved.parents:
        raise StageError(f"{member} points outside {root}")
    return resolved


def qt_core_binary(qt_dir: Path, target: str) -> Path | None:
    """Locate the Qt Core binary inside a PyQt6-Qt6 ``Qt6`` directory."""
    candidates = {
        "linux": [qt_dir / "lib" / "libQt6Core.so.6"],
        "windows": [qt_dir / "bin" / "Qt6Core.dll"],
        "macos": [qt_dir / "lib" / "QtCore.framework" / "Versions" / "A" / "QtCore"],
    }[target.split("-")[0]]
    return next((path for path in candidates if path.is_file()), None)


def installed_pyqt_qt_dir() -> Path | None:
    """Return the ``Qt6`` directory of the PyQt6 that PyInstaller will bundle."""
    try:
        import PyQt6  # noqa: F401  (imported for its location only)
    except ImportError:
        return None
    qt_dir = Path(PyQt6.__file__).resolve().parent / "Qt6"
    return qt_dir if qt_dir.is_dir() else None


def check_qt_compatibility(staged_files: list[Path], qt_core: Path | None) -> None:
    """Fail when the staged libraries need a Qt Core feature the wheel lacks."""
    if qt_core is None:
        raise StageError(
            "Could not find the PyQt6-Qt6 Qt Core library. Install the project "
            "(pip install '.[dev]') before staging Breeze, or pass --qt-dir."
        )
    users = [
        path.name for path in staged_files if ZSTD_RESOURCE_MARKER in path.read_bytes()
    ]
    if users and ZSTD_RESOURCE_MARKER not in qt_core.read_bytes():
        raise StageError(
            "The staged KDE libraries cannot load into the bundled Qt.\n"
            f"  {', '.join(sorted(users))} were built with zstd-compressed Qt "
            "resources and import qResourceFeatureZstd from Qt Core,\n"
            f"  but {qt_core} (PyQt6-Qt6 wheel) was built without zstd.\n"
            "Breeze would fail to load and the app would fall back to another "
            "style. Rebuild those frameworks from source against the official "
            "Qt SDK: add them to this target's 'rebuild' section in "
            "scripts/breeze_craft_pins.json."
        )


def installed_pyqt_qt_version() -> str | None:
    """Return the runtime Qt version of the installed PyQt6 (the PyQt6-Qt6 wheel)."""
    try:
        from PyQt6.QtCore import qVersion
    except ImportError:
        return None
    return qVersion()


def check_sdk_matches_wheel(sdk_version: str, wheel_version: str | None) -> None:
    """Frameworks built against the SDK use Qt private API, so versions must match."""
    if wheel_version != sdk_version:
        raise StageError(
            f"The frameworks are built against Qt {sdk_version}, but the installed "
            f"PyQt6-Qt6 is Qt {wheel_version or '(not installed)'}. Install "
            f"PyQt6-Qt6=={sdk_version}, or update qt_sdks in the pins."
        )


# -- building frameworks from source -------------------------------------------


def qt_sdk_dir(
    pins: dict, sdk_name: str, work_dir: Path, cache_dir: Path, sevenzip: str, opener
) -> Path:
    """Download and unpack the pinned official Qt SDK; return its prefix."""
    sdks = pins["qt_sdks"]
    try:
        sdk = sdks["sdks"][sdk_name]
    except KeyError:
        raise StageError(f"No pinned Qt SDK named {sdk_name}") from None
    prefix = work_dir / "qt"
    stamp = prefix / ".pinned-sdk.json"
    expected = json.dumps({"version": sdks["version"], **sdk}, sort_keys=True)
    if stamp.is_file() and stamp.read_text(encoding="utf-8") == expected:
        return prefix
    if prefix.exists():
        shutil.rmtree(prefix)
    for archive in sdk["archives"]:
        local = download(
            sdks["base_url"] + sdk["path"] + archive["file"],
            cache_dir / "qt-sdk" / sdk_name / archive["file"],
            archive["sha256"],
            opener=opener,
        )
        # Most archives unpack at the SDK root; some (Linux ICU) go below it.
        extract(local, prefix / archive.get("subdir", ""), sevenzip)
    if not (prefix / "lib" / "cmake" / "Qt6" / "Qt6Config.cmake").is_file():
        raise StageError(f"The Qt SDK in {prefix} has no lib/cmake/Qt6")
    stamp.write_text(expected, encoding="utf-8")
    return prefix


def merge_trees(sources: list[Path], destination: Path) -> None:
    """Overlay unpacked packages into one prefix that CMake can search."""
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for source in sources:
        shutil.copytree(source, destination, symlinks=True, dirs_exist_ok=True)


def apply_patch(source_dir: Path, patch: Path, strip: int) -> None:
    """Apply a pinned patch with ``git apply``, outside any enclosing repository."""
    git = shutil.which("git")
    if not git:
        raise StageError("git is required to apply the pinned source patches")
    env = dict(os.environ, GIT_CEILING_DIRECTORIES=str(source_dir.parent))
    try:
        subprocess.run(
            [git, "apply", f"-p{strip}", str(patch)],
            cwd=source_dir,
            env=env,
            check=True,
        )
    except subprocess.CalledProcessError:
        raise StageError(f"{patch.name} does not apply to {source_dir.name}") from None


def gettext_tool(name: str, craft_prefix: Path) -> str | None:
    """Find a gettext tool, preferring the pinned Craft gettext package."""
    suffix = ".exe" if sys.platform == "win32" else ""
    bundled = craft_prefix / "bin" / f"{name}{suffix}"
    if sys.platform == "win32" and bundled.is_file():
        return str(bundled)
    return shutil.which(name)


def cmake_command(
    framework: dict,
    source_dir: Path,
    build_dir: Path,
    prefix: Path,
    search_path: list[Path],
    extra_args: list[str],
    tools: dict[str, str],
) -> list[str]:
    """Return the CMake configure command for one framework."""
    return [
        tools["cmake"],
        "-S",
        str(source_dir),
        "-B",
        str(build_dir),
        "-G",
        "Ninja",
        f"-DCMAKE_MAKE_PROGRAM={tools['ninja']}",
        "-DCMAKE_BUILD_TYPE=Release",
        f"-DCMAKE_INSTALL_PREFIX={prefix.as_posix()}",
        "-DCMAKE_PREFIX_PATH=" + ";".join(path.as_posix() for path in search_path),
        "-DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF",
        "-DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=OFF",
        "-DBUILD_TESTING=OFF",
        "-DBUILD_QCH=OFF",
        f"-DPython_EXECUTABLE={Path(sys.executable).as_posix()}",
        f"-DPython3_EXECUTABLE={Path(sys.executable).as_posix()}",
        f"-DGETTEXT_MSGFMT_EXECUTABLE={tools['msgfmt']}",
        f"-DGETTEXT_MSGMERGE_EXECUTABLE={tools['msgmerge']}",
        *framework.get("cmake_args", []),
        *extra_args,
    ]


def check_resolved_packages(cache_file: Path, allowed: list[Path]) -> None:
    """Fail if CMake resolved a KF6, Qt6 or ECM package outside the pins."""
    roots = [os.path.normcase(str(path.resolve())) for path in allowed]
    strays = []
    for line in cache_file.read_text(encoding="utf-8", errors="replace").splitlines():
        match = PINNED_PACKAGE_DIR.match(line)
        if not match or match.group(2).endswith("-NOTFOUND"):
            continue
        found = os.path.normcase(str(Path(match.group(2)).resolve()))
        if not any(found == root or found.startswith(root + os.sep) for root in roots):
            strays.append(f"{match.group(1)} -> {match.group(2)}")
    if strays:
        raise StageError(
            "The framework build used packages from the build machine instead of "
            "the pinned Qt SDK and Craft packages:\n  " + "\n  ".join(strays)
        )


def build_tools(craft_prefix: Path) -> dict[str, str]:
    tools = {
        "cmake": shutil.which("cmake"),
        "ninja": shutil.which("ninja"),
        "msgfmt": gettext_tool("msgfmt", craft_prefix),
        "msgmerge": gettext_tool("msgmerge", craft_prefix),
    }
    missing = sorted(name for name, path in tools.items() if not path)
    if missing:
        raise StageError(
            f"Building the KDE frameworks needs {', '.join(missing)} on PATH "
            "(CMake, Ninja and gettext; and a C++ compiler)."
        )
    try:
        import lxml  # noqa: F401  (breeze-icons generates its 24px icons with it)
    except ImportError:
        raise StageError(
            "breeze-icons needs the lxml Python module: pip install lxml"
        ) from None
    # Forward slashes: CMake reads backslashes in -D values as escapes.
    return {name: Path(str(path)).as_posix() for name, path in tools.items()}


def rebuild_digest(pins: dict, spec: dict) -> str:
    """Identify a framework build by everything that goes into it."""
    rebuild = spec["rebuild"]
    inputs = {
        "recipe": RECIPE_VERSION,
        "qt_sdk": pins["qt_sdks"]["sdks"][rebuild["qt_sdk"]],
        "qt_version": pins["qt_sdks"]["version"],
        "frameworks": [
            pins["framework_sources"][name] for name in rebuild["frameworks"]
        ],
        "rebuild": rebuild,
        "craft": [package["sha256"] for package in spec["packages"]],
    }
    return hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()


def build_frameworks(
    pins: dict,
    spec: dict,
    unpacked: dict[str, Path],
    work_dir: Path,
    cache_dir: Path,
    sevenzip: str,
    opener=None,
) -> Path:
    """Build the target's ``rebuild`` frameworks; return their install prefix."""
    rebuild = spec["rebuild"]
    prefix = work_dir / "p"
    stamp = prefix / ".pinned-build"
    digest = rebuild_digest(pins, spec)
    if stamp.is_file() and stamp.read_text(encoding="utf-8") == digest:
        print(f"Reusing the KDE frameworks built in {prefix}")
        return prefix

    qt_prefix = qt_sdk_dir(
        pins, rebuild["qt_sdk"], work_dir, cache_dir, sevenzip, opener
    )
    craft_prefix = work_dir / "craft"
    merge_trees(list(unpacked.values()), craft_prefix)
    tools = build_tools(craft_prefix)
    if prefix.exists():
        shutil.rmtree(prefix)
    search_path = [prefix, qt_prefix, craft_prefix]
    env = dict(os.environ)
    if sys.platform == "win32":
        # Build-time tools (rcc, qrcAlias, ...) load Qt and Craft DLLs.
        env["PATH"] = os.pathsep.join(
            [str(prefix / "bin"), str(qt_prefix / "bin"), str(craft_prefix / "bin")]
            + [env.get("PATH", "")]
        )

    sources_root = work_dir / "src"
    if sources_root.exists():
        shutil.rmtree(sources_root)
    for name in rebuild["frameworks"]:
        framework = pins["framework_sources"][name]
        archive = download(
            framework["url"],
            cache_dir / "sources" / Path(framework["url"]).name,
            framework["sha256"],
            opener=opener,
        )
        extract(archive, sources_root, sevenzip)
        source_dir = sources_root / framework["directory"]
        for patch in framework.get("patches", []):
            patch_file = download(
                patch["url"],
                cache_dir / "sources" / Path(patch["url"]).name,
                patch["sha256"],
                opener=opener,
            )
            apply_patch(source_dir, patch_file, patch.get("strip", 1))

        build_dir = work_dir / "b" / name
        if build_dir.exists():
            shutil.rmtree(build_dir)
        print(
            f"Building {name} {framework['version']} against Qt from {qt_prefix}",
            flush=True,
        )
        configure = cmake_command(
            framework,
            source_dir,
            build_dir,
            prefix,
            search_path,
            rebuild.get("cmake_args", []),
            tools,
        )
        try:
            subprocess.run(configure, check=True, env=env)
            check_resolved_packages(build_dir / "CMakeCache.txt", search_path)
            subprocess.run(
                [tools["cmake"], "--build", str(build_dir)], check=True, env=env
            )
            subprocess.run(
                [tools["cmake"], "--install", str(build_dir)], check=True, env=env
            )
        except subprocess.CalledProcessError as error:
            raise StageError(
                f"Building {name} failed (exit code {error.returncode})"
            ) from None
    stamp.write_text(digest, encoding="utf-8")
    return prefix


# -- staging ---------------------------------------------------------------------


def macos_fix_install_names(files: list[Path]) -> None:
    """Point absolute install names at @rpath and re-sign ad hoc."""
    tool = shutil.which("install_name_tool")
    otool = shutil.which("otool")
    codesign = shutil.which("codesign")
    if not (tool and otool and codesign):
        raise StageError("install_name_tool, otool and codesign are required on macOS")
    names = {path.name for path in files}
    for path in files:
        output = subprocess.run(
            [otool, "-L", str(path)], capture_output=True, text=True, check=True
        ).stdout.splitlines()[1:]
        args = []
        for line in output:
            dep = line.strip().split(" (")[0]
            base = os.path.basename(dep)
            if dep.startswith("/") and base in names:
                args += ["-change", dep, f"@rpath/{base}"]
        if path.suffix == ".dylib":
            args += ["-id", f"@rpath/{path.name}"]
        load_commands = subprocess.run(
            [otool, "-l", str(path)], capture_output=True, text=True, check=True
        ).stdout
        rpaths = [
            line.split()[1]
            for line in (raw.strip() for raw in load_commands.splitlines())
            if line.startswith("path ")
        ]
        # Build-machine rpaths (Craft root, Qt SDK, build prefix) mean nothing
        # in the bundle; the app's libraries sit next to each other.
        for rpath in dict.fromkeys(rpaths):
            if rpath.startswith("/"):
                args += ["-delete_rpath", rpath]
        wanted = ["@loader_path"]
        if path.suffix == ".so":
            wanted.append("@loader_path/../../lib")
        args += [
            item
            for rpath in wanted
            if rpath not in rpaths
            for item in ("-add_rpath", rpath)
        ]
        if args:
            subprocess.run([tool, *args, str(path)], check=True)
        subprocess.run([codesign, "--force", "--sign", "-", str(path)], check=True)


def shipped_components(pins: dict, spec: dict) -> list[dict]:
    """Every package or source build with files in the bundle, for the notice."""
    used_packages = {spec["plugin"]["package"]}
    used_frameworks = set()
    for library in spec["libraries"]:
        if "framework" in library:
            used_frameworks.add(library["framework"])
        else:
            used_packages.add(library["package"])
    components = [
        dict(package, origin="craft")
        for package in spec["packages"]
        if package["name"] in used_packages
    ]
    for name in spec.get("rebuild", {}).get("frameworks", []):
        if name in used_frameworks:
            components.append(
                dict(pins["framework_sources"][name], name=name, origin="source")
            )
    return components


def copy_licenses(stage_dir: Path, components: list[dict], license_dir: Path) -> list:
    """Copy the full license texts the shipped components need.

    Each component names a directory below ``licenses/breeze/`` that holds the
    license files from that project's own source release. Returns the copied
    files relative to the stage directory.
    """
    destination = stage_dir / STAGED_LICENSE_DIR
    destination.mkdir()
    copied = []
    for name in sorted({item["license_dir"] for item in components}):
        source = license_dir / name
        texts = sorted(path for path in source.glob("*") if path.is_file())
        if not texts:
            raise StageError(f"No license texts in {source}")
        (destination / name).mkdir()
        for text in texts:
            shutil.copy2(text, destination / name / text.name)
            copied.append(f"{STAGED_LICENSE_DIR}/{name}/{text.name}")
    return copied


def write_notice(stage_dir: Path, target: str, pins: dict, components: list) -> None:
    lines = [
        "KDE Breeze style for Qt 6 and supporting libraries",
        "=" * 50,
        "",
        "Files marked 'craft' are unmodified binaries from the KDE Craft binary",
        f"cache (release {pins['craft_release']}, target {target}).",
    ]
    if any(item["origin"] == "source" for item in components):
        lines += [
            "Files marked 'source' were built by scripts/stage_breeze.py from the",
            "KDE source release listed, against the official Qt "
            f"{pins['qt_sdks']['version']} SDK.",
        ]
    lines += [
        "Every archive was verified by SHA-256. Corresponding source code is",
        "available from the projects listed below. Full license texts are in",
        f"the {STAGED_LICENSE_DIR}/ directory next to this file.",
        "",
    ]
    for item in components:
        lines += [
            f"{item['name']} {item['version']} ({item['origin']})",
            f"  license: {item['license']}",
            f"  texts:   {STAGED_LICENSE_DIR}/{item['license_dir']}/",
            f"  source:  {item['source']}",
        ]
        if item["origin"] == "craft":
            lines.append(f"  archive: {item['file']}")
        else:
            lines.append(f"  tarball: {item['url']}")
            for patch in item.get("patches", []):
                lines.append(f"  patch:   {patch['url']} (sha256 {patch['sha256']})")
        lines += [f"  sha256:  {item['sha256']}", ""]
    (stage_dir / NOTICE_NAME).write_text("\n".join(lines), encoding="utf-8")


def stage(
    target: str,
    dest_root: Path = DEFAULT_DEST,
    cache_dir: Path = DEFAULT_CACHE,
    qt_dir: Path | None = None,
    pins: dict | None = None,
    skip_compat_check: bool = False,
    opener=None,
    work_dir: Path | None = None,
    license_dir: Path = LICENSE_DIR,
) -> Path:
    pins = pins or load_pins()
    spec = target_pins(pins, target)
    base_url = pins["base_url"].format(craft_path=spec["craft_path"])
    sevenzip = find_7z()
    work_dir = work_dir or cache_dir / target / "kf6"
    stage_dir = dest_root / target
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    (stage_dir / "plugins" / "styles").mkdir(parents=True)
    (stage_dir / "lib").mkdir()

    if "rebuild" in spec and not skip_compat_check and qt_dir is None:
        check_sdk_matches_wheel(pins["qt_sdks"]["version"], installed_pyqt_qt_version())
    packages = spec["packages"] + spec.get("rebuild", {}).get("build_packages", [])
    with tempfile.TemporaryDirectory(prefix="breeze-stage-") as scratch:
        unpacked = {}
        for package in packages:
            archive = download(
                base_url + package["file"],
                cache_dir / target / Path(package["file"]).name,
                package["sha256"],
                opener=opener,
            )
            unpacked[package["name"]] = Path(scratch) / package["name"].replace(
                "/", "_"
            )
            extract(archive, unpacked[package["name"]], sevenzip)
        built = None
        if "rebuild" in spec:
            built = build_frameworks(
                pins, spec, unpacked, work_dir, cache_dir, sevenzip, opener
            )

        plugin = spec["plugin"]
        plugin_source = resolve_member(unpacked[plugin["package"]], plugin["member"])
        plugin_dest = stage_dir / "plugins" / "styles" / Path(plugin["member"]).name
        shutil.copy2(plugin_source, plugin_dest)
        staged = [plugin_dest]
        for library in spec["libraries"]:
            if "framework" in library:
                if built is None:
                    raise StageError(
                        f"{library['member']} comes from a source build, but "
                        f"{target} has no 'rebuild' section"
                    )
                root = built
            else:
                root = unpacked[library["package"]]
            source = resolve_member(root, library["member"])
            destination = stage_dir / "lib" / Path(library["member"]).name
            shutil.copy2(source, destination)
            staged.append(destination)

    if not skip_compat_check:
        qt_dir = qt_dir or installed_pyqt_qt_dir()
        check_qt_compatibility(
            staged, qt_core_binary(qt_dir, target) if qt_dir else None
        )
    if target.startswith("macos"):
        macos_fix_install_names(staged)

    components = shipped_components(pins, spec)
    licenses = copy_licenses(stage_dir, components, license_dir)
    write_notice(stage_dir, target, pins, components)
    manifest = {
        "target": target,
        "plugin": str(plugin_dest.relative_to(stage_dir).as_posix()),
        "libraries": sorted(
            path.relative_to(stage_dir).as_posix() for path in staged[1:]
        ),
        "notice": NOTICE_NAME,
        "licenses": licenses,
    }
    (stage_dir / STAGE_MANIFEST).write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Breeze staged for {target} in {stage_dir}")
    return stage_dir


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--target", help="Pins target (default: this machine)")
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="Where to unpack the Qt SDK and build frameworks (keep it short on "
        "Windows; default: <cache>/<target>/kf6)",
    )
    parser.add_argument(
        "--pins", type=Path, default=PINS_FILE, help="Pins file (default: %(default)s)"
    )
    parser.add_argument(
        "--qt-dir",
        type=Path,
        help="PyQt6 Qt6 directory to check against (default: installed PyQt6)",
    )
    args = parser.parse_args(argv)
    try:
        target = args.target or current_target()
        stage(
            target,
            args.dest,
            args.cache,
            args.qt_dir,
            pins=load_pins(args.pins),
            work_dir=args.work_dir,
        )
    except StageError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
