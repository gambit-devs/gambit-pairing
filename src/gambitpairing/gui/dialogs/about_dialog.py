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

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gambitpairing import APP_NAME, APP_VERSION
from gambitpairing.resources.resource_utils import (
    get_resource_path,
    read_resource_text,
)


class AboutDialog(QDialog):
    """Modern about dialog with tabbed interface showing app info and license."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setMinimumSize(320, 460)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        """
        Set up the modern tabbed user interface.

        Creates a tabbed dialog with About and License tabs, along with a Close button.
        Sets appropriate sizing, layout, and styling for all components.

        Notes
        -----
        Sets minimum dialog size to 400x600 pixels and default size to 450x350 pixels. #
        Uses zero margins on main layout for edge-to-edge tab display.
        """
        # Set minimum size for the dialog
        self.setMinimumSize(300, 400)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create tab widget
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet(
            """
            QTabBar {
                qproperty-expanding: true;
            }
            QTabBar::tab {
                min-width: 80px;
            }
        """
        )
        tab_widget.addTab(self._create_about_tab(), "About")
        tab_widget.addTab(self._create_license_tab(), "License")

        # Make sure tab widget expands properly
        tab_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        main_layout.addWidget(tab_widget)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(20, 15, 20, 20)
        button_layout.addStretch()

        ok_button = QPushButton("Close")
        ok_button.clicked.connect(self.accept)
        ok_button.setMinimumWidth(100)
        ok_button.setStyleSheet("font-weight: 500; padding: 8px 16px;")
        button_layout.addWidget(ok_button)

        main_layout.addLayout(button_layout)

    def _create_about_tab(self):
        """
        Create the About tab widget with application information.

        Returns
        -------
        QWidget
            A widget containing centered application information including name,
            description, and support links.

        Notes
        -----
        The tab contains:
        - Application name and subtitle
        - Brief description
        - Discord community support link
        - All content is vertically centered with appropriate spacing
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 20, 10, 10)
        layout.setSpacing(15)

        # Logo/Icon
        logo_label = QLabel()
        icon_path = get_resource_path("icon.png", subpackage="icons")
        logo_pixmap = QPixmap(str(icon_path))
        # Scale to fit within 300x300 maximum
        max_size = 160
        scaled_pixmap = logo_pixmap.scaled(
            max_size,
            max_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        logo_label.setPixmap(scaled_pixmap)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)

        # App name and version
        app_name = QLabel("Gambit Pairing")
        app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_name.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(app_name)

        version_label = QLabel(f"{APP_NAME} : {APP_VERSION}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("font-size: 9px; color: dimgrey;")
        layout.addWidget(version_label)

        # Description
        description = QLabel("Fast, fair and modern tournament management")
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 10px; line-height: 1.4;")
        layout.addWidget(description)

        # Support info
        support_text = QLabel("For support, join our <a href='#'>Discord community</a>")
        support_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        support_text.setOpenExternalLinks(True)
        support_text.setStyleSheet("font-size: 10px; margin-top: 10px;")
        layout.addWidget(support_text)

        # Add stretch to center content vertically
        layout.addStretch()

        return widget

    def _create_license_tab(self):
        """
        Create the License tab widget with legal information.

        Returns
        -------
        QWidget
            A widget containing a scroll-able text area with the MIT License text.

        Notes
        -----
        Features:
        - Read-only QTextEdit with MIT License text
        - Monospace font for legal document formatting
        - Scrollable for longer license texts
        - margins around the text area
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 20, 10, 10)

        # License text in a scroll-able area
        license_text = QTextEdit()
        license_text.setReadOnly(True)
        gpl = read_resource_text("LICENSE")
        license_text.setPlainText(gpl)
        license_text.setStyleSheet(
            """
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                font-family: monospace;
                font-size: 7px;
            }
        """
        )
        license_text.setReadOnly(True)

        layout.addWidget(license_text)

        return widget
