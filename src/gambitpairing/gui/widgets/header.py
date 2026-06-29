"""Header for displaying tabs."""

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

from collections.abc import Callable

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt

from gambitpairing.gui.gui_utils import get_colored_icon, set_svg_icon
from gambitpairing.gui.ui_loader import load_ui_into, required_child


class TabHeader(QtWidgets.QWidget):
    """A universal header widget for all tabs.

    Displays a title, an optional icon, and a container for action buttons.
    """

    def __init__(
        self,
        title: str,
        icon_name: str | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        load_ui_into(self, "tab_header.ui")

        self.icon_label = required_child(self, QtWidgets.QLabel, "icon_label")
        self.title_label = required_child(self, QtWidgets.QLabel, "title_label")
        self.actions_layout = required_child(
            self, QtWidgets.QHBoxLayout, "actions_layout"
        )

        self.title_label.setText(title)
        if icon_name:
            set_svg_icon(self.icon_label, icon_name, "#2d5a27", 24)
            self.icon_label.show()

    def set_title(self, title: str) -> None:
        """Set the title."""
        self.title_label.setText(title)

    def add_action_button(
        self, icon_name: str, tooltip: str, callback: Callable[[], object]
    ) -> QtWidgets.QPushButton:
        """Add action button to the header."""
        btn = QtWidgets.QPushButton()
        icon = get_colored_icon(icon_name, "#2d5a27", 24)
        btn.setIcon(icon)
        btn.setProperty("class", "IconButton")
        btn.setToolTip(tooltip)
        btn.clicked.connect(callback)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.actions_layout.addWidget(btn)
        return btn
