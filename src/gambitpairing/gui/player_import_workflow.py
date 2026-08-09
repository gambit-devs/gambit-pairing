"""Qt-facing workflow for importing players from federation APIs."""

from __future__ import annotations

from PyQt6 import QtWidgets

from gambitpairing.controllers.player import get_player_import_availability
from gambitpairing.gui.dialogs import PlayerManagementDialog


class PlayerImportWorkflow:
    """Coordinate the API import dialog and refresh affected views."""

    def __init__(self, main_window) -> None:
        self.main_window = main_window

    def import_players_from_api(self) -> None:
        """Open the federation API tab when the tournament permits imports."""
        availability = get_player_import_availability(self.main_window.tournament)
        if not availability.allowed:
            QtWidgets.QMessageBox.warning(
                self.main_window,
                availability.title,
                availability.message,
            )
            return

        dialog = PlayerManagementDialog(
            parent=self.main_window,
            tournament=self.main_window.tournament,
        )
        dialog.tab_widget.setCurrentIndex(1)
        if dialog.exec():
            self.main_window.players_tab.refresh_player_list()
            self.main_window.players_tab.update_ui_state()
            self.main_window.mark_dirty()
