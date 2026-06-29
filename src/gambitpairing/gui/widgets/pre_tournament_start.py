"""Pre-tournament start widget."""

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

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import Qt

from gambitpairing.gui.gui_utils import set_svg_icon
from gambitpairing.gui.ui_loader import load_ui_into, required_child


class PreTournamentStart(QtWidgets.QWidget):
    """A centered widget displayed when a tournament is loaded but not yet started."""

    start_requested = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        load_ui_into(self, "pre_tournament_start.ui")

        self.icon_label = required_child(self, QtWidgets.QLabel, "icon_label")
        self.title_label = required_child(self, QtWidgets.QLabel, "title_label")
        self.desc_label = required_child(self, QtWidgets.QLabel, "desc_label")
        self.btn_start = required_child(self, QtWidgets.QPushButton, "btn_start")

        set_svg_icon(self.icon_label, "play.svg", "#2d5a27", 64)
        self.title_label.setText("Ready to Start")
        self.desc_label.setText(
            "The tournament is set up and ready to begin.\n"
            "Click the button below to generate the first round pairings."
        )
        self.btn_start.setText("Start Tournament")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self.start_requested.emit)


#  LocalWords:  PreTournamentLabel PreTournamentTitle PreTournamentWidget
