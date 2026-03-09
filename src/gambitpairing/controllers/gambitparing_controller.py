"""Main controller for gambit-pairing."""

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

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from gambitpairing.core.club import Club
from gambitpairing.exceptions import FileLoadException
from gambitpairing.gui import GambitPairingMainWindow
from gambitpairing.models.tournament import Tournament


from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


# BIG 'ol WIP
class GampitPairingController:
    """Central application controller.

    Attributes
    ----------
    TODO
    """

    def __init__(self) -> None:
        # TODO: Figure out the main window
        self.app: QtWidgets.QApplication
        self.main_window = GambitPairingMainWindow()
        self.window.set_app_instance(app)
        self.window.show()
        logger.info("Setup main window")
        self.tournament: Optional[Tournament] = None
        self.current_round_index: int = 0
        self.last_recorded_results_data: List[Tuple[str, str, float]] = []
        self.tournament_save_filepath: Optional[Path] = None
        self.dirty: bool = False

    def set_application_icon(self) -> None:
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
        icon = QIcon(icon_path)

        if icon and isinstance(icon, QIcon):
            app.setWindowIcon(icon)
            logger.info("Successfully set application icon")
        else:
            raise IconException(
                "icon not a QIcon, icon instance of type(%s)", type(icon)
            )

    def set_application_style(self) -> None:
        """Set application style.

        Parameters
        ----------
        app : QtWidgets.QApplication
        The app to set the style for

        Returns
        -------
        None

        Raises
        ------
        StyleException
            When style fails to be set
        """
        # Bind variable here to satisfy static type-checkers even if an exception
        # is raised before it is assigned inside the try block.
        style_text = ""
        try:
            style_text = get_style_sheet()  # uses the active theme (dark by default)

            logger.debug("style_text: (%s)\n", style_text)
            self.app.setStyleSheet(style_text)

        except Exception as e:
            raise StyleException(
                "Exception (%s)\n raised when setting app style. style_text: \n %s",
                e,
                style_text,
            )

    def save_tournament(self) -> None:
        """Save the active tournament."""
        logger.info("trying to save tournament.")
        path = self._prompt_save_path()
        if not path:
            logger.info("_prompt_save_path() returned Nothing.")
            raise FileLoadException("_prompt_save_path() returned Nothing.")
        try:
            self.persistence.save(self.app, path)
            self._refresh_ui()
        except SaveError as e:
            self._show_error("Save Error", str(e))
            raise e

    def reset_tournament_state(self):
        """Reset the entire application to a clean state."""
        self.tournament = None
        self.current_round_index = 0
        self.last_recorded_results_data = []
        self.current_tournament_filepath = None
        self.mark_clean()

        self._set_tournament_on_tabs()  # clear tournament tabs

        # Clear tab UI
        self.players_tab.reset_display()
        self.rounds_tab.reset_display()
        self.standings_tab.reset_display()
        self.crosstable_tab.reset_display()
        self.history_tab.reset_display()

        self._update_ui_state()

    def mark_clean(self) -> None:
        """Mask app state as clean."""
        self.dirty = False

    def mark_dirty(self):
        """Mark app state as 'dirty'."""
        self._dirty = True
        self._update_ui_state()


from pathlib import Path
import platform
import sys

from PyQt6 import QtWidgets
from PyQt6.QtCore import QDir
from PyQt6.QtGui import QIcon
from importlib_resources import files

from gambitpairing.exceptions import IconException, StyleException
from gambitpairing.gui import GambitPairingMainWindow
from gambitpairing.controllers import GampitPairingController
from gambitpairing.resources.resource_utils import (
    get_resource_path,
    get_style_sheet,
)
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


def main():
    """Entry point."""
    # Register the icons directory as the "icons:" search-path prefix so QSS
    # url(icons:arrow-up.svg) references resolve at runtime.
    icon_path = str(Path(str(files("gambitpairing.resources.icons"))))
    QDir.setSearchPaths("icons", [icon_path])
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


def set_application_style(app: QtWidgets.QApplication) -> None:
    """Set application style.

    Parameters
    ----------
    app : QtWidgets.QApplication
       The app to set the style for

    Returns
    -------
    None

    Raises
    ------
    StyleException
        When style fails to be set
    """
    # Bind variable here to satisfy static type-checkers even if an exception
    # is raised before it is assigned inside the try block.
    style_text = ""
    try:
        style_text = get_style_sheet()  # uses the active theme (dark by default)

        logger.debug("style_text: (%s)\n", style_text)
        app.setStyleSheet(style_text)
        logger.debug("Applied stylesheet (%d chars)", len(style_text))

    except Exception as e:
        raise StyleException(
            "Exception (%s)\n raised when setting app style. style_text: \n %s",
            e,
            style_text,
        )


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

    # Set cross-platform application icon
    set_application_icon(app)
    # Get current platform
    system = platform.system()

    if system == "Windows":
        app.setStyle("WindowsVista")  # windows
    elif system == "Darwin":  # macOS
        app.setStyle("macos")
    else:
        app.setStyle("fusion")  # Best cross-platform option

    # set app style
    set_application_style(app)
    app.controller = GampitPairingController()

    exit_code = app.exec()
    return exit_code


if __name__ == "__main__":
    main()

#  LocalWords:  IconException QIcon WindowsVista macos StyleException
