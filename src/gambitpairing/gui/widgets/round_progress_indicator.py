"""
Reusable UI widgets for the Tournament tab.

This module contains Qt widgets used in the tournament management interface:
- ResultSelector: A widget for selecting game results (1-0, ½-½, 0-1)
- RoundProgressIndicator: Native progress bar showing tournament progress
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

from __future__ import annotations

from PyQt6 import QtWidgets

from gambitpairing.gui.ui_loader import load_ui_into, required_child
from gambitpairing.models.enums import TournamentPhase


class RoundProgressIndicator(QtWidgets.QWidget):
    """
    A visual progress indicator showing the current round and tournament status.

    Uses a native QProgressBar and a text summary.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        load_ui_into(self, "round_progress_indicator.ui")
        self.progress_bar = required_child(self, QtWidgets.QProgressBar, "progress_bar")
        self.progress_label = required_child(self, QtWidgets.QLabel, "progress_label")

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

        # Keep an indeterminate-looking empty state out of the native bar.
        if total_rounds <= 0:
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(0)
            self.progress_label.setText("Tournament not configured")
            return

        self.progress_bar.setRange(0, total_rounds)
        completed_rounds = (
            total_rounds
            if phase == TournamentPhase.FINISHED
            else max(0, min(total_rounds, current_round - 1))
        )
        self.progress_bar.setValue(completed_rounds)

        # Update progress text
        if phase == TournamentPhase.FINISHED:
            self.progress_label.setText(f"Tournament Complete ({total_rounds} rounds)")
        elif phase == TournamentPhase.NOT_STARTED:
            self.progress_label.setText(f"{total_rounds} rounds planned")
        else:
            self.progress_label.setText(f"Round {current_round} of {total_rounds}")
