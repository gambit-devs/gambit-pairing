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

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal


class TournamentPlaceholder(QtWidgets.QWidget):
    """Placeholder widget shown when no tournament is loaded."""

    create_tournament_requested = pyqtSignal()
    import_tournament_requested = pyqtSignal()

    def __init__(self, parent=None, tab_name=""):
        super().__init__(parent)
        self.tab_name = tab_name
        self._setup_ui()

    def _setup_ui(self):
        """Set up the placeholder UI."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(0)

        # Add spacer to center content vertically
        layout.addStretch()

        # Icon/Symbol
        icon_label = QtWidgets.QLabel("♟️")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setProperty("class", "NoTournamentIcon")
        layout.addWidget(icon_label)

        # Main message
        title_label = QtWidgets.QLabel("No Tournament Loaded")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setProperty("class", "NoTournamentMainMessage")
        layout.addWidget(title_label)

        # Description
        desc_text = (
            f"The {self.tab_name} tab will be available once you create a tournament."
        )
        if not self.tab_name:
            desc_text = "Create a tournament to begin managing your chess competition."

        desc_label = QtWidgets.QLabel(desc_text)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)

        desc_label.setProperty("class", "NoTournamentDescription")
        layout.addWidget(desc_label)

        # Action buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(18)

        # Create Tournament Button
        self.create_btn = QtWidgets.QPushButton("Create Tournament")
        self.create_btn.clicked.connect(self.create_tournament_requested.emit)
        self.create_btn.setProperty("class", "NoTournamentCreateTournament")

        # Import Tournament Button
        self.import_btn = QtWidgets.QPushButton("Import Tournament")
        self.import_btn.clicked.connect(self.import_tournament_requested.emit)
        self.import_btn.setProperty("class", "NoTournamentImportTournament")

        # Center the buttons
        button_layout.addStretch()
        button_layout.addWidget(self.create_btn)
        button_layout.addWidget(self.import_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Add spacer to center content vertically
        layout.addStretch()

        self.setProperty("class", "TournamentPlaceholder")


#  LocalWords:  NoTournament NoTournamentIcon TournamentPlaceholder NoTournamentImportTournament NoTournamentCreateTournament
