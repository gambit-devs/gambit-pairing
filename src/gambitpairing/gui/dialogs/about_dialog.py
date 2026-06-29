"""About dialog for Gambit Pairing."""

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

from PyQt6.QtGui import QPixmap
from PyQt6 import QtCore, QtWidgets

from gambitpairing import APP_NAME, APP_VERSION
from gambitpairing.gui.ui_loader import load_ui_into, required_child
from gambitpairing.resources.resource_utils import (
    get_resource_path,
    read_resource_text,
)


class AboutDialog(QtWidgets.QDialog):
    """Modern about dialog with tabbed interface showing app info and license."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "AboutDialog")
        load_ui_into(self, "about_dialog.ui")
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Wire runtime data and behavior to the Designer-defined layout."""
        self.setWindowTitle(f"About {APP_NAME}")

        self.tab_widget = required_child(
            self, QtWidgets.QTabWidget, "tab_widget"
        )
        self.logo_label = required_child(self, QtWidgets.QLabel, "logo_label")
        self.app_name_label = required_child(
            self, QtWidgets.QLabel, "app_name_label"
        )
        self.version_label = required_child(
            self, QtWidgets.QLabel, "version_label"
        )
        self.description_label = required_child(
            self, QtWidgets.QLabel, "description_label"
        )
        self.support_label = required_child(
            self, QtWidgets.QLabel, "support_label"
        )
        self.license_text = required_child(
            self, QtWidgets.QTextEdit, "license_text"
        )
        self.close_button = required_child(
            self, QtWidgets.QPushButton, "close_button"
        )

        self._load_logo()
        self.version_label.setText(f"{APP_NAME} : {APP_VERSION}")
        self.license_text.setPlainText(read_resource_text("LICENSE"))
        self.close_button.clicked.connect(self.accept)

    def _load_logo(self) -> None:
        """Load and scale the package icon for the About tab."""
        icon_path = get_resource_path("icon.png", subpackage="icons")
        logo_pixmap = QPixmap(str(icon_path))
        max_size = 160
        scaled_pixmap = logo_pixmap.scaled(
            max_size,
            max_size,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
        self.logo_label.setPixmap(scaled_pixmap)
