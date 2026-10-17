"""Gambit Pairing entry point."""

# Gambit Pairing
# Copyright (C) 2025  Gambit Pairing developers
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
from pathlib import Path
import sys

from PyQt6 import QtWidgets
from PyQt6.QtCore import QCoreApplication, QLibraryInfo
from PyQt6.QtGui import QIcon

from gambitpairing.exceptions import IconException
from gambitpairing.gui import GambitPairingMainWindow
from gambitpairing.resources.resource_utils import get_resource_path
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


# Directory below sys._MEIPASS that holds Qt plugins bundled by the release
# build (the Breeze style). Keep in sync with scripts/pyinstaller_common.py.
BUNDLED_QT_PLUGIN_DIR = "qt_plugins"


def is_frozen() -> bool:
    """Return True when running from a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))


def bundled_qt_plugin_dir() -> Path | None:
    """Return the bundled Qt plugin directory of a frozen build, if any."""
    if not is_frozen():
        return None
    bundle_root = getattr(sys, "_MEIPASS", None) or Path(sys.executable).parent
    return Path(bundle_root) / BUNDLED_QT_PLUGIN_DIR


def add_bundled_qt_plugin_path() -> None:
    """Make Qt find plugins shipped inside a frozen build (Breeze)."""
    plugin_dir = bundled_qt_plugin_dir()
    if plugin_dir is None:
        return
    if not plugin_dir.is_dir():
        logger.warning("Bundled Qt plugin directory is missing: %s", plugin_dir)
        return
    QCoreApplication.addLibraryPath(str(plugin_dir))
    logger.info("Added bundled Qt plugin path: %s", plugin_dir)


def add_host_breeze_plugin_paths(app: QtWidgets.QApplication) -> None:
    """Expose an installed Linux Breeze style plugin to a source install.

    Frozen builds never use host plugins; they ship their own Breeze.
    """
    if not sys.platform.startswith("linux"):
        return
    if is_frozen():
        return

    plugin_paths = [
        Path("/usr/lib64/qt6/plugins"),
        Path("/usr/lib/qt6/plugins"),
        Path("/usr/local/lib64/qt6/plugins"),
        Path("/usr/local/lib/qt6/plugins"),
    ]
    for library_root in (Path("/usr/lib"), Path("/usr/local/lib")):
        plugin_paths.extend(library_root.glob("*/qt6/plugins"))

    known_paths = {str(Path(path).resolve()) for path in app.libraryPaths()}
    for plugin_path in plugin_paths:
        style_dir = plugin_path / "styles"
        try:
            has_breeze = any(
                "breeze" in plugin.name.casefold() and plugin.is_file()
                for plugin in style_dir.iterdir()
            )
        except OSError:
            continue
        if not has_breeze:
            continue

        resolved_path = str(plugin_path.resolve())
        if resolved_path not in known_paths:
            QCoreApplication.addLibraryPath(resolved_path)
            known_paths.add(resolved_path)
            logger.info("Added host Qt plugin path for Breeze: %s", resolved_path)


def configure_native_style(app: QtWidgets.QApplication) -> str:
    """Select Breeze when its native Qt Widgets style plugin is available.

    Frozen builds load the Breeze plugin bundled with the app. Source installs
    can use a host Breeze plugin on Linux.

    Returns
    -------
    str
        The active Qt style name.

    Raises
    ------
    RuntimeError
        When ``GAMBIT_NATIVE_STYLE_REQUIRED=1`` and Breeze could not be loaded.
    """
    add_bundled_qt_plugin_path()
    add_host_breeze_plugin_paths(app)

    active_qstyle = app.style()
    if active_qstyle is None:
        raise RuntimeError("QApplication has no active Qt style")
    active_style = active_qstyle.objectName()

    available_styles = {
        style_name.casefold(): style_name
        for style_name in QtWidgets.QStyleFactory.keys()
    }
    if active_style.casefold() != "breeze" and "breeze" in available_styles:
        breeze_style = QtWidgets.QStyleFactory.create(available_styles["breeze"])
        if breeze_style is not None:
            app.setStyle(breeze_style)
            active_qstyle = app.style()
            if active_qstyle is not None:
                active_style = active_qstyle.objectName()

    if active_style.casefold() == "breeze":
        if not QIcon.themeName():
            QIcon.setThemeName("breeze")
        logger.info("Using native Breeze style (icon theme: %s)", QIcon.themeName())
        return active_style

    if os.environ.get("GAMBIT_NATIVE_STYLE_REQUIRED") == "1":
        raise RuntimeError(
            "Breeze was required but the Qt runtime could not load its style plugin "
            f"(active style: {active_style!r})"
        )

    logger.warning(
        "Breeze Qt style plugin is unavailable; keeping Qt style %r. "
        "Qt plugin paths: %s",
        active_style,
        QCoreApplication.libraryPaths(),
    )

    return active_style


def run_velopack_hooks() -> None:
    """Run Velopack's startup hooks (install, update and uninstall events).

    Velopack requires this to run before any other startup code in the main
    process. It may exit or restart the process. Only packaged (frozen) builds
    can be Velopack installs, so source runs skip it.
    """
    if not is_frozen():
        return
    try:
        import velopack
    except ImportError:
        logger.debug("velopack is not installed; skipping its startup hooks")
        return
    # Apply an update that was downloaded but not yet installed (for example
    # when the user chose "Later" after the download finished).
    velopack.App().set_auto_apply_on_startup(True).run()


def main():
    """Entry point."""
    import multiprocessing

    # freeze_support() only acts in spawned pairing worker processes (where it
    # never returns); in the main process it is a no-op, so Velopack's hooks
    # are still the first startup code the main process runs.
    multiprocessing.freeze_support()
    run_velopack_hooks()
    exit_code = run_app()
    logger.info("run_app() exited with code: %s", exit_code)
    sys.exit(exit_code)


def set_application_icon(app: QtWidgets.QApplication) -> None:
    """Set application icon.

    Parameters
    ----------
    app : QtWidgets.QApplication
       The app to set the icon for

    Returns
    -------
    None

    Raises
    ------
    IconException
        When icon is not a QIcon
    """
    icon_path = get_resource_path("icon.png", subpackage="icons")

    logger.info("icon_path: (%s)\n", icon_path)
    icon = QIcon(str(icon_path))

    if icon and isinstance(icon, QIcon):
        app.setWindowIcon(icon)
        logger.info("Successfully set application icon")
    else:
        raise IconException("icon not a QIcon, icon instance of type(%s)", type(icon))


def verify_native_style(app: QtWidgets.QApplication, active_style: str) -> int:
    """Report the active style; frozen builds must be running Breeze.

    Returns
    -------
    int
        0 on success, 1 when a frozen build is not using its bundled Breeze.
    """
    message = (
        f"Native style check: style={active_style.casefold()}, "
        f"available_styles={QtWidgets.QStyleFactory.keys()}, "
        f"frozen={is_frozen()}, library_paths={QCoreApplication.libraryPaths()}, "
        f"qt_plugins={QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)}"
    )
    logger.info(message)
    # Frozen GUI builds on Windows have no console; the log above still records it.
    if sys.stdout is not None:
        print(message, flush=True)
    if is_frozen() and active_style.casefold() != "breeze":
        logger.error("Frozen build is not using its bundled Breeze style")
        return 1
    return 0


def run_app() -> int:
    """Run the gui application.

    Returns
    -------
    int
        the exit code from app.exec()

    Raises
    ------
    IconException
        When icon is not a QIcon
    """
    app = QtWidgets.QApplication(sys.argv)

    active_style = configure_native_style(app)

    if "--verify-native-style" in sys.argv:
        return verify_native_style(app, active_style)

    # Set cross-platform application icon
    set_application_icon(app)

    window = GambitPairingMainWindow()
    if "--smoke-test" in sys.argv:
        from gambitpairing.smoke import check_tournament_round_trip

        check_tournament_round_trip()
        window.deleteLater()
        return 0
    window.show()

    exit_code = app.exec()
    return exit_code


if __name__ == "__main__":
    main()

#  LocalWords:  IconException QIcon
