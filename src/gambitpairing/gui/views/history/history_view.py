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


import logging

from PyQt6 import QtGui, QtWidgets
from PyQt6.QtCore import QDateTime

from gambitpairing.gui.notournament_placeholder import NoTournamentPlaceholder
from gambitpairing.gui.widgets.header import TabHeader


class HistoryView(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tournament = None
        self.main_layout = QtWidgets.QVBoxLayout(self)

        # Header
        self.header = TabHeader("History Log")
        self.main_layout.addWidget(self.header)

        # History group
        self.history_group = QtWidgets.QGroupBox()
        self.history_group.setStyleSheet("QGroupBox { border: none; margin-top: 0px; }")
        history_layout = QtWidgets.QVBoxLayout(self.history_group)
        history_layout.setContentsMargins(0, 0, 0, 0)

        self.history_view = QtWidgets.QPlainTextEdit()
        self.history_view.setReadOnly(True)
        self.history_view.setToolTip("Log of pairings, results, and actions.")
        font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
        self.history_view.setFont(font)
        history_layout.addWidget(self.history_view)
        self.main_layout.addWidget(self.history_group)

        # Add no tournament placeholder
        self.no_tournament_placeholder = NoTournamentPlaceholder(self, "History Log")
        self.no_tournament_placeholder.create_tournament_requested.connect(
            self._trigger_create_tournament
        )
        self.no_tournament_placeholder.import_tournament_requested.connect(
            self._trigger_import_tournament
        )
        self.no_tournament_placeholder.hide()
        self.main_layout.addWidget(self.no_tournament_placeholder)

    def set_tournament(self, tournament):
        self.tournament = tournament
        self._update_visibility()

    def _update_visibility(self):
        """Show/hide content based on tournament existence."""
        if not self.tournament:
            self.no_tournament_placeholder.show()
            self.history_group.hide()
        else:
            self.no_tournament_placeholder.hide()
            self.history_group.show()

    def update_history_log(self, message: str):
        if self.tournament:  # Only log when tournament exists
            timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
            self.history_view.appendPlainText(f"[{timestamp}] {message}")
            logging.info(
                f"UI_LOG: {message}"
            )  # Distinguish from backend logging if needed

    def update_ui_state(self):
        self._update_visibility()

    def _trigger_create_tournament(self):
        parent = self.parent()
        while parent is not None:
            if hasattr(parent, "prompt_new_tournament"):
                parent.prompt_new_tournament()
                return
            parent = parent.parent()

    def _trigger_import_tournament(self):
        parent = self.parent()
        while parent is not None:
            if hasattr(parent, "load_tournament"):
                parent.load_tournament()
                return
            parent = parent.parent()
