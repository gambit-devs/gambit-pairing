"""Main GUI window for Gambit Pairing."""

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

from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMessageBox

from gambitpairing import APP_VERSION
from gambitpairing.exceptions import FileLoadException
from gambitpairing.type_aliases import Players
from gambitpairing.utils import setup_logger
from gambitpairing.controllers import GampitPairingController

logger = setup_logger(__name__)


class GambitPairingMainWindow(QtWidgets.QMainWindow):
    """Main application window.

    UI setup and management only.
    """

    def __init__(
        self, controller: GampitPairingController, persistence: TournamentPersistence
    ):
        super().__init__()

        self.controller = controller
        self.persistence = persistence

        self.updater = Updater(APP_VERSION)

        self._setup_ui()
        self._connect_signals()
        self._refresh_ui()

    def get_confirmation(
        self, action="", message="Are you sure you want to proceed?"
    ) -> bool:
        """Get confirmation from user before proceeding."""
        reply = QMessageBox.question(
            self,
            action,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(self, "Success", "Action completed!")
            logger.info("confirmation granted.")
            return True

        logger.info("confirmation denied.")
        return False

    def prompt_new_tournament(self) -> None:
        dialog = NewTournamentDialog(self)
        if not dialog.exec():
            return

        data = dialog.get_data()
        if not data:
            return

        tournament = TournamentFactory.create(*data)
        self.app.new_tournament(tournament)

        self._propagate_tournament()
        self._refresh_ui()
        self._notify(f"New tournament '{tournament.name}' created")

    def load_tournament(self) -> None:
        """Prompt user for tournament file, and load the tournament save @ path."""
        path = self._prompt_load_path()
        if not path:
            logger.warning("No file path returned by _prompt_load_path, returning.")
            return

        try:
            self._propagate_tournament()
            self._refresh_ui()
        except FileLoadException as e:
            self._show_error("Load Error", str(e))

    def _refresh_ui(self) -> None:
        state = compute_ui_state(self.app)

        self._update_actions(state)
        self._update_toolbar(state)
        self._update_status_bar(state)

    def _show_error(self, error_text: str) -> None:
