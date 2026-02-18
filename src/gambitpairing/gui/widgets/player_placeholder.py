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

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal


class PlayerPlaceholder(QtWidgets.QWidget):
    """Placeholder widget shown when tournament exists but no players added."""

    import_players_requested = pyqtSignal()
    add_player_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the placeholder UI."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(0)

        # Add spacer to center content vertically
        layout.addStretch()

        # Icon/Symbol
        icon_label = QtWidgets.QLabel("👥")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label.set(Qt.AlignmentFlag.AlignCenter)
        icon_label.setProperty("class", "PlayerPlaceHolderIcon")
        layout.addWidget(icon_label)

        # Main message
        title_label = QtWidgets.QLabel("No Players Added")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setProperty("class", "PlayerPlaceholderTitle")
        layout.addWidget(title_label)

        # Description
        desc_label = QtWidgets.QLabel("Add players to your tournament to get started.")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        desc_label.setProperty("class", "PlayerPlaceholderDesc")
        layout.addWidget(desc_label)

        # Action buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(18)

        self.import_btn = QtWidgets.QPushButton("Import Players")
        self.import_btn.clicked.connect(self.import_players_requested.emit)
        self.import_btn.setProperty("class", "ImportPlayerButton")

        self.add_btn = QtWidgets.QPushButton("Add Player")
        self.add_btn.clicked.connect(self.add_player_requested.emit)
        self.add_btn.setProperty("class", "ImportPlayerButton")
        button_layout.addStretch()
        button_layout.addWidget(self.import_btn)
        button_layout.addWidget(self.add_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Add spacer to center content vertically
        layout.addStretch()
