"""
Unified printing utilities for tournament management.
This module provides shared functionality for generating print content across different tabs.
"""

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


import re
from typing import Tuple

from PyQt6 import QtWidgets
from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog


class TournamentPrintUtils:
    """Utility class for unified tournament printing functionality."""

    @staticmethod
    def get_round_info(rounds_tab) -> str:
        """
        Get unified round information from rounds tab.

        Args:
            rounds_tab: Reference to the rounds tab widget

        Returns:
            Clean round information string for display
        """
        round_title = ""
        if hasattr(rounds_tab, "header") and hasattr(rounds_tab.header, "title_label"):
            round_title = rounds_tab.header.title_label.text()
        elif hasattr(rounds_tab, "lbl_round_title"):
            round_title = rounds_tab.lbl_round_title.text()

        if not round_title or round_title == "No Tournament Loaded":
            return ""

        # Extract round information and clean it
        if "Round" in round_title:
            match = re.search(r"Round (\d+)", round_title)
            if match:
                round_num = int(match.group(1))
                # Check completion status
                if "Results" in round_title and hasattr(
                    rounds_tab, "current_round_index"
                ):
                    completed_rounds = rounds_tab.current_round_index
                    if round_num <= completed_rounds:
                        return f"After Round {round_num}"
                    else:
                        return f"During Round {round_num}"
                else:
                    return f"After Round {round_num}"

        return ""

    @staticmethod
    def get_clean_print_title(round_title: str) -> str:
        """
        Clean round title for print display.

        Args:
            round_title: Raw round title string

        Returns:
            Cleaned title suitable for printing
        """
        if not round_title:
            return ""

        # Remove common UI elements that shouldn't appear in print
        clean_title = round_title.replace(" Pairings & Results", " Pairings")
        clean_title = clean_title.replace(" (Re-entry)", "")
        return clean_title

    @staticmethod
    def create_print_preview_dialog(
        parent, title: str
    ) -> Tuple[QPrinter, QPrintPreviewDialog]:
        """
        Create a print preview dialog with standard settings.

        Args:
            parent: Parent widget
            title: Window title for the preview dialog

        Returns:
            Tuple of (printer, preview_dialog)
        """
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        preview = QPrintPreviewDialog(printer, parent)
        preview.setWindowTitle(title)

        # Customize the toolbar to remove the zoom dropdown
        # Find the toolbar in the dialog
        toolbar = preview.findChild(QtWidgets.QToolBar)
        if toolbar:
            # Iterate through actions to find the zoom combo box
            for action in toolbar.actions():
                widget = toolbar.widgetForAction(action)
                if isinstance(widget, QtWidgets.QComboBox):
                    # Found the zoom combo box, replace it with a label
                    # We can't easily replace the widget in the action, but we can hide the action
                    # and insert a label. However, QPrintPreviewDialog is a bit rigid.
                    # A simpler approach is to just hide the combo box if possible,
                    # or accept that we can't easily modify the internal QPrintPreviewDialog toolbar
                    # without more complex hacking.

                    # Let's try to find the zoom input and replace/modify it
                    # The zoom combo is usually populated with percentages.

                    # Alternative: Create a custom preview dialog that inherits QPrintPreviewDialog
                    # and overrides the toolbar creation, but that's complex.

                    # Let's try to just set it to editable or replace it if we can access it.
                    # Since the user asked to "replace it with either a read-only display... or a simple input field",
                    # and this is a standard Qt dialog, modifying it is tricky.

                    # However, we can try to find the specific widget and modify its properties.
                    widget.setEditable(True)
                    widget.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
                    # Make it look more like a line edit
                    widget.setStyleSheet(
                        "QComboBox { border: 1px solid #ccc; padding: 2px; }"
                    )
                    break

        return printer, preview


def create_print_button(label: str, tooltip: str = "") -> QtWidgets.QPushButton:
    """Create a standardized print button for use in tabs.

    This helper centralizes the visual affordance used for Print buttons
    across the app so they look and behave consistently.

    Args:
        label: The text label for the button (e.g. "Print Standings").
        tooltip: Optional tooltip to set on the button.

    Returns:
        Configured QPushButton instance.
    """
    btn = QtWidgets.QPushButton(label)
    if tooltip:
        btn.setToolTip(tooltip)
    return btn


class PrintOptionsDialog(QtWidgets.QDialog):
    """Custom dialog for print options including tournament name inclusion."""

    def __init__(
        self, parent=None, tournament_name: str = "", print_type: str = "Document"
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Print Options - {print_type}")
        self.setModal(True)
        self.setMinimumWidth(300)
        layout = QtWidgets.QVBoxLayout(self)
        # No checkbox, just info label
        if tournament_name:
            info_label = QtWidgets.QLabel(
                f"Tournament name '{tournament_name}' will be included in the printout."
            )
            info_label.setWordWrap(True)
            layout.addWidget(info_label)
        layout.addSpacing(10)
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        self.setStyleSheet(
            """
            QDialog {
                background-color: #f8f9fa;
            }
            QLabel {
                font-size: 11pt;
                padding: 5px;
            }
            QPushButton {
                font-size: 11pt;
                padding: 6px 12px;
                min-width: 70px;
            }
        """
        )

    def get_options(self) -> dict:
        return {"include_tournament_name": True}
