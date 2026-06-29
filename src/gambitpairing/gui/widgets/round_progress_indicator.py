"""
Reusable UI widgets for the Tournament tab.

This module contains custom Qt widgets used in the tournament management interface:
- CheckableButton: A toggle button with a visual checkmark indicator
- ResultSelector: A widget for selecting game results (1-0, ½-½, 0-1)
- RoundProgressIndicator: Visual indicator showing tournament progress
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

from __future__ import annotations  # this removes the need for " around types

# and removes the need for:
# from typing import TYPE_CHECKING

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt

from gambitpairing.gui.gui_utils import set_svg_icon
from gambitpairing.gui.ui_loader import load_ui_into, required_child
from gambitpairing.models.enums import TournamentPhase


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
        load_ui_into(self, "round_progress_indicator.ui")
        self.dots_container = required_child(
            self, QtWidgets.QWidget, "dots_container"
        )
        self.dots_layout = required_child(
            self, QtWidgets.QHBoxLayout, "dots_layout"
        )
        self.progress_label = required_child(
            self, QtWidgets.QLabel, "progress_label"
        )

        self._dots: list[QtWidgets.QLabel] = []
        self._current_round = 0
        self._total_rounds = 0

    def update_progress(
        self, current_round: int, total_rounds: int, phase: TournamentPhase
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
