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


class NoTournamentPlaceholder(QtWidgets.QWidget):
    """Consistent placeholder widget shown when no tournament is loaded."""

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
        icon_label.setStyleSheet(
            """
            QLabel {
                font-size: 54pt;
                margin-bottom: 18px;
                color: #2d5a27;
            }
        """
        )
        layout.addWidget(icon_label)

        # Main message
        title_label = QtWidgets.QLabel("No Tournament Loaded")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            """
            QLabel {
                font-size: 20pt;
                font-weight: 700;
                color: #2d5a27;
                margin-bottom: 10px;
                letter-spacing: 0.01em;
            }
        """
        )
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
        desc_label.setStyleSheet(
            """
            QLabel {
                font-size: 13pt;
                color: #8b5c2b;
                margin-bottom: 32px;
                line-height: 1.5;
                font-weight: 500;
            }
        """
        )
        layout.addWidget(desc_label)

        # Action buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(18)

        # Create Tournament Button
        self.create_btn = QtWidgets.QPushButton("Create Tournament")
        self.create_btn.clicked.connect(self.create_tournament_requested.emit)
        self.create_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #2d5a27;
                color: #fff;
                font-size: 13pt;
                font-weight: 700;
                padding: 13px 32px;
                border: none;
                border-radius: 10px;
                min-width: 170px;
                letter-spacing: 0.01em;
            }
            QPushButton:hover {
                background-color: #e2c290;
                color: #2d5a27;
            }
            QPushButton:pressed {
                background-color: #8b5c2b;
                color: #fff;
            }
        """
        )

        # Import Tournament Button
        self.import_btn = QtWidgets.QPushButton("Import Tournament")
        self.import_btn.clicked.connect(self.import_tournament_requested.emit)
        self.import_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #e2c290;
                color: #2d5a27;
                font-size: 13pt;
                font-weight: 700;
                padding: 13px 32px;
                border: none;
                border-radius: 10px;
                min-width: 170px;
                letter-spacing: 0.01em;
            }
            QPushButton:hover {
                background-color: #2d5a27;
                color: #fff;
            }
            QPushButton:pressed {
                background-color: #8b5c2b;
                color: #fff;
            }
        """
        )

        # Center the buttons
        button_layout.addStretch()
        button_layout.addWidget(self.create_btn)
        button_layout.addWidget(self.import_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Add spacer to center content vertically
        layout.addStretch()

        # Set overall styling
        self.setStyleSheet(
            """
            NoTournamentPlaceholder {
                background-color: #fffbe9;
                border: 2px solid #e2c290;
                border-radius: 18px;
            }
        """
        )


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
        icon_label.setStyleSheet(
            """
            QLabel {
                font-size: 54pt;
                margin-bottom: 18px;
                color: #2d5a27;
            }
        """
        )
        layout.addWidget(icon_label)

        # Main message
        title_label = QtWidgets.QLabel("No Players Added")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            """
            QLabel {
                font-size: 20pt;
                font-weight: 700;
                color: #2d5a27;
                margin-bottom: 10px;
                letter-spacing: 0.01em;
            }
        """
        )
        layout.addWidget(title_label)

        # Description
        desc_label = QtWidgets.QLabel("Add players to your tournament to get started.")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(
            """
            QLabel {
                font-size: 13pt;
                color: #8b5c2b;
                margin-bottom: 32px;
                line-height: 1.5;
                font-weight: 500;
            }
        """
        )
        layout.addWidget(desc_label)

        # Action buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(18)

        self.import_btn = QtWidgets.QPushButton("Import Players")
        self.import_btn.clicked.connect(self.import_players_requested.emit)
        self.import_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #e2c290;
                color: #2d5a27;
                font-size: 12pt;
                font-weight: 700;
                padding: 12px 28px;
                border: none;
                border-radius: 10px;
                min-width: 140px;
                letter-spacing: 0.01em;
            }
            QPushButton:hover {
                background-color: #2d5a27;
                color: #fff;
            }
            QPushButton:pressed {
                background-color: #8b5c2b;
                color: #fff;
            }
        """
        )

        self.add_btn = QtWidgets.QPushButton("Add Player")
        self.add_btn.clicked.connect(self.add_player_requested.emit)
        self.add_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #2d5a27;
                color: #fff;
                font-size: 12pt;
                font-weight: 700;
                padding: 12px 28px;
                border: none;
                border-radius: 10px;
                min-width: 140px;
                letter-spacing: 0.01em;
            }
            QPushButton:hover {
                background-color: #e2c290;
                color: #2d5a27;
            }
            QPushButton:pressed {
                background-color: #8b5c2b;
                color: #fff;
            }
        """
        )

        button_layout.addStretch()
        button_layout.addWidget(self.import_btn)
        button_layout.addWidget(self.add_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Add spacer to center content vertically
        layout.addStretch()

        # Set overall styling
        self.setStyleSheet(
            """
            PlayerPlaceholder {
                background-color: #fffbe9;
                border: 2px solid #e2c290;
                border-radius: 18px;
            }
        """
        )
