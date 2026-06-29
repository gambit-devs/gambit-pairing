"""Consistent placeholder widget shown when no tournament is loaded."""

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
from PyQt6.QtCore import pyqtSignal

from gambitpairing.gui.ui_loader import load_ui_into, required_child


class TournamentPlaceholder(QtWidgets.QWidget):
    """Placeholder widget shown when no tournament is loaded."""

    create_tournament_requested = pyqtSignal()
    import_tournament_requested = pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None, tab_name: str = ""):
        super().__init__(parent)
        self.tab_name = tab_name
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the placeholder UI."""
        load_ui_into(self, "tournament_placeholder.ui")

        self.icon_label = required_child(self, QtWidgets.QLabel, "icon_label")
        self.title_label = required_child(self, QtWidgets.QLabel, "title_label")
        self.desc_label = required_child(self, QtWidgets.QLabel, "desc_label")
        self.create_btn = required_child(self, QtWidgets.QPushButton, "create_btn")
        self.import_btn = required_child(self, QtWidgets.QPushButton, "import_btn")

        desc_text = (
            f"The {self.tab_name} tab will be available once you create a tournament."
        )
        if not self.tab_name:
            desc_text = "Create a tournament to begin managing your chess competition."

        self.icon_label.setText("♟️")
        self.title_label.setText("No Tournament Loaded")
        self.desc_label.setText(desc_text)
        self.create_btn.setText("Create Tournament")
        self.import_btn.setText("Import Tournament")

        self.create_btn.clicked.connect(self.create_tournament_requested.emit)
        self.import_btn.clicked.connect(self.import_tournament_requested.emit)


#  LocalWords:  NoTournament NoTournamentIcon TournamentPlaceholder NoTournamentImportTournament NoTournamentCreateTournament
