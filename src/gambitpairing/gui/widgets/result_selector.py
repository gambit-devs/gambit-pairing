"""Selector widget for reporting match results."""

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

from PyQt6 import QtWidgets

from gambitpairing.constants import RESULT_BLACK_WIN, RESULT_DRAW, RESULT_WHITE_WIN
from gambitpairing.gui.ui_loader import load_ui_into, required_child

from .checkable_button import CheckableButton


class ResultSelector(QtWidgets.QWidget):
    """
    A widget for selecting chess game results.

    Displays three mutually exclusive buttons for:
    - White wins (1-0)
    - Draw (½-½)
    - Black wins (0-1)

    The selected result can be retrieved via selectedResult() and
    programmatically set via setResult().
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        load_ui_into(self, "result_selector.ui")

        self.button_group = QtWidgets.QButtonGroup(self)
        self.button_group.setExclusive(True)

        self.btn_white_win = required_child(
            self, CheckableButton, "btn_white_win"
        )
        self.btn_draw = required_child(self, CheckableButton, "btn_draw")
        self.btn_black_win = required_child(
            self, CheckableButton, "btn_black_win"
        )

        self.btn_white_win.setText("1-0")
        self.btn_white_win.setProperty("result_const", RESULT_WHITE_WIN)
        self.btn_white_win.setProperty("result_type", "white")
        self.btn_white_win.setToolTip("White wins")

        self.btn_draw.setText("½-½")
        self.btn_draw.setProperty("result_const", RESULT_DRAW)
        self.btn_draw.setProperty("result_type", "draw")
        self.btn_draw.setToolTip("Draw")

        self.btn_black_win.setText("0-1")
        self.btn_black_win.setProperty("result_const", RESULT_BLACK_WIN)
        self.btn_black_win.setProperty("result_type", "black")
        self.btn_black_win.setToolTip("Black wins")

        buttons = [self.btn_white_win, self.btn_draw, self.btn_black_win]
        for btn in buttons:
            self.button_group.addButton(btn)

    def selectedResult(self) -> str:
        """
        Get the currently selected result.

        Returns
        -------
        str
            The result constant (RESULT_WHITE_WIN, RESULT_DRAW, or RESULT_BLACK_WIN),
            or empty string if no result is selected.
        """
        checked_button = self.button_group.checkedButton()
        return checked_button.property("result_const") if checked_button else ""

    def setResult(self, result_constant: str) -> None:
        """
        Programmatically set the selected result.

        Parameters
        ----------
        result_constant : str
            One of RESULT_WHITE_WIN, RESULT_DRAW, or RESULT_BLACK_WIN.
            If the value doesn't match any button, the selection is cleared.
        """
        for button in self.button_group.buttons():
            if button.property("result_const") == result_constant:
                button.setChecked(True)
                return
        # If no match, clear selection
        checked_button = self.button_group.checkedButton()
        if checked_button:
            self.button_group.setExclusive(False)
            checked_button.setChecked(False)
            self.button_group.setExclusive(True)


#  LocalWords:  setResult ResultSelector
