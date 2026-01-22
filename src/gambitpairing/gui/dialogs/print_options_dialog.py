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
Print Options Dialog for selecting what tournament documents to print.

This dialog allows users to select whether to print:
- Just the current round pairings
- Just the standings
- Both pairings and standings together
"""

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt


class PrintOptionsDialog(QtWidgets.QDialog):
    """
    Dialog for selecting print options.

    Provides checkboxes for selecting what to include in the print output:
    pairings, standings, or both.
    """

    def __init__(
        self,
        parent=None,
        has_pairings: bool = True,
        has_standings: bool = True,
        round_info: str = "",
        default_pairings: bool = True,
        default_standings: bool = False,
    ):
        """
        Initialize the print options dialog.

        Parameters
        ----------
        parent : QWidget, optional
            Parent widget
        has_pairings : bool
            Whether pairings are available to print
        has_standings : bool
            Whether standings are available to print
        round_info : str
            Current round information for display
        default_pairings : bool
            Whether pairings checkbox is checked by default
        default_standings : bool
            Whether standings checkbox is checked by default
        """
        super().__init__(parent)
        self.setWindowTitle("Print Options")
        self.setMinimumWidth(450)  # Increased width for better visibility
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        self._has_pairings = has_pairings
        self._has_standings = has_standings
        self._default_pairings = default_pairings
        self._default_standings = default_standings

        self._setup_ui(round_info)

    def _setup_ui(self, round_info: str):
        """Create the dialog UI."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(20)  # Increased spacing
        layout.setContentsMargins(32, 32, 32, 32)  # Increased padding

        # Header
        header_label = QtWidgets.QLabel("Select Documents to Print")
        header_label.setProperty("class", "DialogHeader")
        font = header_label.font()
        font.setPointSize(12)
        font.setBold(True)
        header_label.setFont(font)
        layout.addWidget(header_label)

        # Round info display
        if round_info:
            info_label = QtWidgets.QLabel(round_info)
            info_label.setProperty("class", "DialogSubtitle")
            info_label.setStyleSheet("color: #666; margin-bottom: 8px;")
            layout.addWidget(info_label)

        # Options container
        options_group = QtWidgets.QGroupBox("Print Selection")
        options_layout = QtWidgets.QVBoxLayout(options_group)
        options_layout.setSpacing(12)

        # Pairings checkbox
        self.chk_pairings = QtWidgets.QCheckBox("Current Round Pairings")
        self.chk_pairings.setChecked(self._has_pairings and self._default_pairings)
        self.chk_pairings.setEnabled(self._has_pairings)
        if not self._has_pairings:
            self.chk_pairings.setToolTip("No pairings available for this round")
        else:
            self.chk_pairings.setToolTip("Include the pairings for the current round")
        options_layout.addWidget(self.chk_pairings)

        # Description for pairings
        pairings_desc = QtWidgets.QLabel(
            "Board assignments with white and black players"
        )
        pairings_desc.setStyleSheet("color: #888; font-size: 9pt; margin-left: 24px;")
        options_layout.addWidget(pairings_desc)

        # Standings checkbox
        self.chk_standings = QtWidgets.QCheckBox("Tournament Standings")
        self.chk_standings.setChecked(self._has_standings and self._default_standings)
        self.chk_standings.setEnabled(self._has_standings)
        if not self._has_standings:
            self.chk_standings.setToolTip(
                "No standings available yet - record results first"
            )
        else:
            self.chk_standings.setToolTip("Include the current tournament standings")
        options_layout.addWidget(self.chk_standings)

        # Description for standings
        standings_desc = QtWidgets.QLabel("Player rankings with scores and tiebreakers")
        standings_desc.setStyleSheet("color: #888; font-size: 9pt; margin-left: 24px;")
        options_layout.addWidget(standings_desc)

        layout.addWidget(options_group)

        # Page break option (only shown when both are selected)
        self.chk_page_break = QtWidgets.QCheckBox("Print on separate pages")
        self.chk_page_break.setChecked(True)
        self.chk_page_break.setToolTip(
            "When checked, pairings and standings will print on separate pages"
        )
        self.chk_page_break.setVisible(False)  # Hidden initially
        layout.addWidget(self.chk_page_break)

        # Connect checkboxes to update page break visibility
        self.chk_pairings.toggled.connect(self._update_page_break_visibility)
        self.chk_standings.toggled.connect(self._update_page_break_visibility)

        # Add stretch
        layout.addStretch()

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(12)

        self.btn_cancel = QtWidgets.QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(self.btn_cancel)

        button_layout.addStretch()

        self.btn_print = QtWidgets.QPushButton("Print Preview")
        self.btn_print.clicked.connect(self._validate_and_accept)
        self.btn_print.setDefault(True)
        button_layout.addWidget(self.btn_print)

        layout.addLayout(button_layout)

        # Update initial state
        self._update_page_break_visibility()

    def _update_page_break_visibility(self):
        """Show/hide page break option based on selections."""
        both_selected = self.chk_pairings.isChecked() and self.chk_standings.isChecked()
        self.chk_page_break.setVisible(both_selected)

        # Update print button enabled state
        any_selected = self.chk_pairings.isChecked() or self.chk_standings.isChecked()
        self.btn_print.setEnabled(any_selected)

    def _validate_and_accept(self):
        """Validate at least one option is selected before accepting."""
        if not self.chk_pairings.isChecked() and not self.chk_standings.isChecked():
            QtWidgets.QMessageBox.warning(
                self, "No Selection", "Please select at least one document to print."
            )
            return
        self.accept()

    def get_options(self) -> dict:
        """
        Get the selected print options.

        Returns
        -------
        dict
            Dictionary with keys:
            - 'print_pairings': bool
            - 'print_standings': bool
            - 'separate_pages': bool
        """
        return {
            "print_pairings": self.chk_pairings.isChecked(),
            "print_standings": self.chk_standings.isChecked(),
            "separate_pages": self.chk_page_break.isChecked(),
        }
