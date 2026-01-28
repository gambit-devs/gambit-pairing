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

"""
Pre-tournament empty state widget.
"""

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt

from gambitpairing.gui.gui_utils import get_colored_icon, set_svg_icon
from gambitpairing.resources.resource_utils import get_resource_path


class PreTournamentWidget(QtWidgets.QWidget):
    """
    A centered widget displayed when a tournament is loaded but not yet started.
    Replaces the empty pairings table.
    """

    start_requested = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "PreTournamentWidget")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(0)

        # Add spacer to center content vertically
        layout.addStretch()

        # Icon
        self.icon_label = QtWidgets.QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Use play icon but with consistent styling
        set_svg_icon(self.icon_label, "play.svg", "#2d5a27", 64)
        self.icon_label.setStyleSheet("margin-bottom: 18px;")
        layout.addWidget(self.icon_label)

        # Title
        self.title_label = QtWidgets.QLabel("Ready to Start")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet(
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
        layout.addWidget(self.title_label)

        # Description
        self.desc_label = QtWidgets.QLabel(
            "The tournament is set up and ready to begin.\n"
            "Click the button below to generate the first round pairings."
        )
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet(
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
        layout.addWidget(self.desc_label)

        # Start Button
        self.btn_start = QtWidgets.QPushButton("Start Tournament")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setMinimumWidth(200)

        # Style the button to match NoTournamentPlaceholder
        self.btn_start.setStyleSheet(
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

        self.btn_start.clicked.connect(self.start_requested.emit)

        # Center button
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_start)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Add spacer to center content vertically
        layout.addStretch()
