"""Placeholder widget shown when no players in a tournament."""

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


class PlayerPlaceholder(QtWidgets.QWidget):
    """Placeholder widget shown when tournament exists but no players added."""

    import_players_requested = pyqtSignal()
    add_player_requested = pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the placeholder UI."""
        self.setProperty("class", "PlayerPlaceholder")
        load_ui_into(self, "player_placeholder.ui")

        self.icon_label = required_child(self, QtWidgets.QLabel, "icon_label")
        self.title_label = required_child(self, QtWidgets.QLabel, "title_label")
        self.desc_label = required_child(self, QtWidgets.QLabel, "desc_label")
        self.import_btn = required_child(self, QtWidgets.QPushButton, "import_btn")
        self.add_btn = required_child(self, QtWidgets.QPushButton, "add_btn")

        self.icon_label.setText("👥")
        self.title_label.setText("No Players Added")
        self.desc_label.setText("Add players to your tournament to get started.")
        self.import_btn.setText("Import Players")
        self.add_btn.setText("Add Player")

        self.import_btn.clicked.connect(self.import_players_requested.emit)
        self.add_btn.clicked.connect(self.add_player_requested.emit)
