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
import sys

from PyQt6 import QtWidgets
from PyQt6.QtCore import QLibraryInfo
from PyQt6.QtGui import QIcon

from gambitpairing.exceptions import IconException
from gambitpairing.gui import GambitPairingMainWindow
from gambitpairing.resources.resource_utils import get_resource_path
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


def configure_native_style(app: QtWidgets.QApplication) -> str:
    """Report the style selected by Qt's platform integration.

    The style is deliberately not assigned here. KDE's platform theme owns
    that decision so the user's selected palette, accent color, font, and
    light/dark preference remain authoritative. The portable Linux bundle
    selects its bundled Breeze plugin before QApplication is constructed;
    this check refuses to hide a broken bundle behind Qt Fusion.

    Returns
    -------
    str
        The active Qt style name.
    """
    active_qstyle = app.style()
    if active_qstyle is None:
        raise RuntimeError("QApplication has no active Qt style")
    active_style = active_qstyle.objectName()
    if active_style.casefold() == "breeze":
        logger.info("Using native Breeze style")
        return active_style

    native_style_required = os.environ.get("GAMBIT_NATIVE_STYLE_REQUIRED") == "1"
    bundled_style_required = (
        os.environ.get("GAMBIT_BUNDLED_QT_RUNTIME") == "1"
        and os.environ.get("GAMBIT_BUNDLED_STYLE_REQUIRED") == "1"
    )
    if native_style_required or bundled_style_required:
        raise RuntimeError(
            "The configured KDE runtime could not load Breeze "
            f"(active style: {active_style!r}); refusing a Fusion fallback"
        )

    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").casefold()
    kde_session = "kde" in desktop or bool(os.environ.get("KDE_FULL_SESSION"))
    available_styles = {
        style_name.casefold(): style_name
        for style_name in QtWidgets.QStyleFactory.keys()
    }

    if kde_session and "breeze" in available_styles:
        logger.warning(
            "KDE selected style %r although compatible Breeze plugin %r is "
            "available; check QT_STYLE_OVERRIDE and the Qt runtime",
            active_style,
            available_styles["breeze"],
        )
    elif kde_session:
        logger.warning(
            "KDE session is using Qt style %r; no compatible Breeze plugin is "
            "visible to this Qt runtime",
            active_style,
        )
    else:
        logger.info("Using Qt platform style: %s", active_style)

    return active_style


def main():
    """Entry point."""
    import multiprocessing

    multiprocessing.freeze_support()
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
        logger.info(
            "Native style check: style=%s, available_styles=%s, stylesheet=%r",
            active_style,
            QtWidgets.QStyleFactory.keys(),
            app.styleSheet(),
        )
        logger.info(
            "Native Qt plugin path: %s",
            QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath),
        )
        return 0

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
