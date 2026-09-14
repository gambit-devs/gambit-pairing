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

from PyQt6 import QtGui, QtWidgets
from PyQt6.QtCore import pyqtSignal

from gambitpairing.gui.gui_utils import get_native_icon
from gambitpairing.gui.ui_loader import load_ui_into, required_child


class RoundControlsWidget(QtWidgets.QWidget):
    """Widget containing the primary tournament controls (Start, Next Round, Record, Undo)."""

    start_requested = pyqtSignal()
    prepare_requested = pyqtSignal()
    record_requested = pyqtSignal()
    undo_requested = pyqtSignal()
    view_standings_requested = pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        load_ui_into(self, "round_controls.ui")

        self.btn_undo = required_child(self, QtWidgets.QPushButton, "btn_undo")
        self.btn_primary_action = required_child(
            self, QtWidgets.QPushButton, "btn_primary_action"
        )
        self.lbl_keyboard_hints = required_child(
            self, QtWidgets.QLabel, "lbl_keyboard_hints"
        )
        self.lbl_progress = required_child(self, QtWidgets.QLabel, "lbl_progress")

        self.btn_undo.setText("Undo")
        self.btn_undo.setIcon(
            get_native_icon("edit-undo", QtWidgets.QStyle.StandardPixmap.SP_ArrowBack)
        )
        self.btn_undo.setToolTip("Undo the last recorded round results")
        self.btn_undo.clicked.connect(self.undo_requested.emit)

        self.btn_primary_action.setText("Start Tournament")
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
            self.btn_primary_action.setIcon(
                get_native_icon(
                    "media-playback-start", QtWidgets.QStyle.StandardPixmap.SP_MediaPlay
                )
            )
            self.btn_primary_action.setEnabled(True)
            self.btn_primary_action.setToolTip(
                "Start the tournament and generate first round pairings"
            )
        elif state == "prepare":
            self.btn_primary_action.setText("Prepare Next Round")
            self.btn_primary_action.setIcon(
                get_native_icon(
                    "view-refresh", QtWidgets.QStyle.StandardPixmap.SP_BrowserReload
                )
            )
            self.btn_primary_action.setEnabled(True)
            self.btn_primary_action.setToolTip("Generate pairings for the next round")
        elif state == "record":
            self.btn_primary_action.setText("Record Results")
            self.btn_primary_action.setIcon(
                get_native_icon(
                    "dialog-ok-apply",
                    QtWidgets.QStyle.StandardPixmap.SP_DialogApplyButton,
                )
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

    def set_progress(self, text: str) -> None:
        """Update the compact result progress label."""
        self.lbl_progress.setText(text)

    def set_keyboard_hints(self, text: str) -> None:
        """Update the keyboard help shown in the footer."""
        self.lbl_keyboard_hints.setText(text)

    def set_primary_action(
        self,
        text: str,
        enabled: bool | None = None,
        tooltip: str | None = None,
    ) -> None:
        """Override the primary action copy for a specific round state."""
        self.btn_primary_action.setText(text)
        if enabled is not None:
            self.btn_primary_action.setEnabled(enabled)
        if tooltip is not None:
            self.btn_primary_action.setToolTip(tooltip)

    def _on_primary_action_clicked(self) -> None:
        if self._primary_action_state == "start":
            self.start_requested.emit()
        elif self._primary_action_state == "prepare":
            self.prepare_requested.emit()
        elif self._primary_action_state == "record":
            self.record_requested.emit()
        elif self._primary_action_state == "finished":
            self.view_standings_requested.emit()
