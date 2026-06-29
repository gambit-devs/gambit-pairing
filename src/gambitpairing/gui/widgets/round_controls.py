"""Control the active round."""

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

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import pyqtSignal

from gambitpairing.gui.gui_utils import get_colored_icon
from gambitpairing.gui.ui_loader import load_ui_into, required_child
from gambitpairing.resources.resource_utils import get_resource_path


class RoundControlsWidget(QtWidgets.QWidget):
    """Widget containing the primary tournament controls (Start, Next Round, Record, Undo)."""

    start_requested = pyqtSignal()
    prepare_requested = pyqtSignal()
    record_requested = pyqtSignal()
    undo_requested = pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        load_ui_into(self, "round_controls.ui")

        self.btn_undo = required_child(self, QtWidgets.QPushButton, "btn_undo")
        self.btn_primary_action = required_child(
            self, QtWidgets.QPushButton, "btn_primary_action"
        )

        self.btn_undo.setText("Undo")
        self.btn_undo.setIcon(get_colored_icon("undo.svg", "#2d5a27", 16))
        self.btn_undo.setToolTip("Undo the last recorded round results")
        self.btn_undo.clicked.connect(self.undo_requested.emit)

        self.btn_primary_action.setText("Start Tournament")
        self.btn_primary_action.setIconSize(QtCore.QSize(16, 16))
        self.btn_primary_action.setToolTip(
            "Start the tournament and generate first round pairings"
        )
        self.btn_primary_action.clicked.connect(self._on_primary_action_clicked)

        # Internal state to track what the primary button should do
        self._primary_action_state = "start"  # start, prepare, record

    def update_state(self, state: str) -> None:
        """
        Update the state of the controls based on tournament phase.

        Args:
            state: One of 'start', 'prepare', 'record', 'finished'
        """
        self._primary_action_state = state

        if state == "start":
            self.btn_primary_action.setText("Start Tournament")
            play_icon_path = get_resource_path("play.svg", subpackage="icons")
            self.btn_primary_action.setIcon(QtGui.QIcon(str(play_icon_path)))
            self.btn_primary_action.setEnabled(True)
            self.btn_primary_action.setToolTip(
                "Start the tournament and generate first round pairings"
            )
        elif state == "prepare":
            self.btn_primary_action.setText("Prepare Next Round")
            refresh_icon_path = get_resource_path("refresh.svg", subpackage="icons")
            self.btn_primary_action.setIcon(QtGui.QIcon(str(refresh_icon_path)))
            self.btn_primary_action.setEnabled(True)
            self.btn_primary_action.setToolTip("Generate pairings for the next round")
        elif state == "record":
            self.btn_primary_action.setText("Record Results")
            self.btn_primary_action.setIcon(
                get_colored_icon("checkmark-white.svg", "black", 16)
            )
            self.btn_primary_action.setEnabled(True)
            self.btn_primary_action.setToolTip("Save results and advance to next round")
        elif state == "finished":
            self.btn_primary_action.setText("Tournament Finished")
            self.btn_primary_action.setIcon(QtGui.QIcon())  # No icon for finished
            self.btn_primary_action.setEnabled(False)
            self.btn_primary_action.setToolTip("All rounds completed")

    def set_undo_enabled(self, enabled: bool) -> None:
        self.btn_undo.setEnabled(enabled)

    def set_undo_visible(self, visible: bool) -> None:
        """Show or hide the undo control."""
        self.btn_undo.setVisible(visible)

    def _on_primary_action_clicked(self) -> None:
        if self._primary_action_state == "start":
            self.start_requested.emit()
        elif self._primary_action_state == "prepare":
            self.prepare_requested.emit()
        elif self._primary_action_state == "record":
            self.record_requested.emit()
