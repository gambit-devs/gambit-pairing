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
Reusable UI widgets for the Tournament tab.

This module contains custom Qt widgets used in the tournament management interface:
- CheckableButton: A toggle button with a visual checkmark indicator
- ResultSelector: A widget for selecting game results (1-0, ½-½, 0-1)
- RoundProgressIndicator: Visual indicator showing tournament progress
"""

from typing import TYPE_CHECKING

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt

from gambitpairing.constants import (
    RESULT_BLACK_WIN,
    RESULT_DRAW,
    RESULT_WHITE_WIN,
)
from gambitpairing.gui.gui_utils import get_colored_icon, set_svg_icon

if TYPE_CHECKING:
    from gambitpairing.gui.views.tournament.tournament_state import TournamentPhase


class RoundProgressIndicator(QtWidgets.QWidget):
    """
    A visual progress indicator showing the current round and tournament status.

    Displays round progress as a series of circles/dots:
    - Completed rounds are filled
    - Current round is highlighted
    - Future rounds are outlined

    Also shows a text summary of tournament progress.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "RoundProgressIndicator")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(12)

        # Progress dots container
        self.dots_container = QtWidgets.QWidget()
        self.dots_layout = QtWidgets.QHBoxLayout(self.dots_container)
        self.dots_layout.setContentsMargins(0, 0, 0, 0)
        self.dots_layout.setSpacing(8)
        layout.addWidget(self.dots_container)

        layout.addStretch()

        # Progress text label
        self.progress_label = QtWidgets.QLabel("")
        self.progress_label.setProperty("class", "ProgressLabel")
        layout.addWidget(self.progress_label)

        self._dots = []
        self._current_round = 0
        self._total_rounds = 0

    def update_progress(
        self, current_round: int, total_rounds: int, phase: "TournamentPhase"
    ):
        """
        Update the progress indicator.

        Parameters
        ----------
        current_round : int
            The current round number (1-indexed)
        total_rounds : int
            Total number of rounds in the tournament
        phase : TournamentPhase
            Current phase of the tournament
        """
        from gambitpairing.gui.tabs.tournament_state import TournamentPhase

        self._current_round = current_round
        self._total_rounds = total_rounds

        # Clear existing dots
        for dot in self._dots:
            dot.deleteLater()
        self._dots.clear()

        # Don't show dots if not started or too many rounds
        if total_rounds <= 0:
            self.progress_label.setText("Tournament not configured")
            return

        # Create dots (limit to 12 visible dots for very long tournaments)
        visible_rounds = min(total_rounds, 12)

        for i in range(visible_rounds):
            round_num = i + 1
            dot = QtWidgets.QLabel()
            dot.setFixedSize(16, 16)
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)

            if round_num < current_round:
                # Completed round
                dot.setProperty("state", "completed")
                set_svg_icon(dot, "checkmark-white.svg", "black", 12)
            elif round_num == current_round:
                # Current round
                if phase == TournamentPhase.AWAITING_RESULTS:
                    dot.setProperty("state", "active")
                elif phase == TournamentPhase.FINISHED:
                    dot.setProperty("state", "completed")
                    set_svg_icon(dot, "checkmark-white.svg", "black", 12)
                else:
                    dot.setProperty("state", "current")
                dot.setText(str(round_num)) if not dot.pixmap() else None
            else:
                # Future round
                dot.setProperty("state", "pending")
                dot.setText(str(round_num))

            self.dots_layout.addWidget(dot)
            self._dots.append(dot)

        # If there are more rounds than visible, add ellipsis
        if total_rounds > visible_rounds:
            ellipsis = QtWidgets.QLabel("...")
            ellipsis.setProperty("class", "ProgressEllipsis")
            self.dots_layout.addWidget(ellipsis)
            self._dots.append(ellipsis)

        # Update progress text
        if phase == TournamentPhase.FINISHED:
            self.progress_label.setText(f"Tournament Complete ({total_rounds} rounds)")
        elif phase == TournamentPhase.NOT_STARTED:
            self.progress_label.setText(f"{total_rounds} rounds planned")
        else:
            self.progress_label.setText(f"Round {current_round} of {total_rounds}")

        # Force style refresh on dots
        for dot in self._dots:
            dot.style().unpolish(dot)
            dot.style().polish(dot)


class CheckableButton(QtWidgets.QPushButton):
    """
    A toggle button that displays a checkmark when checked.

    Used for result selection buttons in the tournament pairings table.
    The checkmark is drawn in the top-right corner when the button is checked.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCheckable(True)
        self.check_icon = get_colored_icon("checkmark-white.svg", "white", 12)
        self.setProperty("class", "ResultSelectorButton")

    def paintEvent(self, a0):
        """Custom paint event to draw checkmark on checked buttons."""
        super().paintEvent(a0)
        if self.isChecked():
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

            rect = self.rect()
            # Move checkmark further left for White win and Draw to avoid clipping
            if self.text() in ["1-0", "½-½"]:
                offset = 20
            else:
                offset = 18
            checkmark_rect = QtCore.QRect(rect.right() - offset, rect.top() + 2, 12, 12)
            if not self.check_icon.isNull():
                self.check_icon.paint(painter, checkmark_rect)
            else:
                # Fallback
                painter.setPen(QtGui.QPen(QtGui.QColor("white"), 2))
                font = QtGui.QFont(painter.font())
                font.setPointSize(10)
                font.setBold(True)
                painter.setFont(font)
                painter.drawText(checkmark_rect, Qt.AlignmentFlag.AlignCenter, "✓")


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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "ResultSelector")

        layout = QtWidgets.QHBoxLayout(self)
        # Add margins to prevent clipping of borders/shadows
        # Increased margins to fix clipping on bottom/right
        layout.setContentsMargins(2, 2, 8, 12)
        layout.setSpacing(0)

        # Enforce minimum size to prevent squashing in table
        self.setMinimumWidth(150)
        self.setMinimumHeight(40)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed
        )

        self.button_group = QtWidgets.QButtonGroup(self)
        self.button_group.setExclusive(True)

        # Create buttons with clear, readable labels
        self.btn_white_win = CheckableButton("1-0")
        self.btn_white_win.setProperty("result_const", RESULT_WHITE_WIN)
        self.btn_white_win.setProperty("result_type", "white")
        self.btn_white_win.setToolTip("White wins")

        self.btn_draw = CheckableButton("½-½")
        self.btn_draw.setProperty("result_const", RESULT_DRAW)
        self.btn_draw.setProperty("result_type", "draw")
        self.btn_draw.setToolTip("Draw")

        self.btn_black_win = CheckableButton("0-1")
        self.btn_black_win.setProperty("result_const", RESULT_BLACK_WIN)
        self.btn_black_win.setProperty("result_type", "black")
        self.btn_black_win.setToolTip("Black wins")

        buttons = [self.btn_white_win, self.btn_draw, self.btn_black_win]
        for btn in buttons:
            self.button_group.addButton(btn)
            layout.addWidget(btn)

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

    def setResult(self, result_constant: str):
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
