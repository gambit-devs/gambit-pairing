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

from gambitpairing.gui.ui_loader import load_ui_into, required_child


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
        self.setProperty("class", "PrintOptionsDialog")
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        self._has_pairings = has_pairings
        self._has_standings = has_standings
        self._default_pairings = default_pairings
        self._default_standings = default_standings

        load_ui_into(self, "print_options_dialog.ui")
        self._setup_ui(round_info)

    def _setup_ui(self, round_info: str):
        """Wire behavior to the Designer-defined dialog UI."""
        self.round_info_label = required_child(
            self, QtWidgets.QLabel, "round_info_label"
        )
        if round_info:
            self.round_info_label.setText(round_info)
            self.round_info_label.show()
        else:
            self.round_info_label.hide()

        self.chk_pairings = required_child(
            self, QtWidgets.QCheckBox, "chk_pairings"
        )
        self.chk_pairings.setChecked(self._has_pairings and self._default_pairings)
        self.chk_pairings.setEnabled(self._has_pairings)
        if not self._has_pairings:
            self.chk_pairings.setToolTip("No pairings available for this round")
        else:
            self.chk_pairings.setToolTip("Include the pairings for the current round")

        self.chk_standings = required_child(
            self, QtWidgets.QCheckBox, "chk_standings"
        )
        self.chk_standings.setChecked(self._has_standings and self._default_standings)
        self.chk_standings.setEnabled(self._has_standings)
        if not self._has_standings:
            self.chk_standings.setToolTip(
                "No standings available yet - record results first"
            )
        else:
            self.chk_standings.setToolTip("Include the current tournament standings")

        self.chk_page_break = required_child(
            self, QtWidgets.QCheckBox, "chk_page_break"
        )

        # Connect checkboxes to update page break visibility
        self.chk_pairings.toggled.connect(self._update_page_break_visibility)
        self.chk_standings.toggled.connect(self._update_page_break_visibility)

        self.btn_cancel = required_child(self, QtWidgets.QPushButton, "btn_cancel")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_print = required_child(self, QtWidgets.QPushButton, "btn_print")
        self.btn_print.clicked.connect(self._validate_and_accept)

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
