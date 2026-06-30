"""Unsaved changes confirmation dialog."""

from __future__ import annotations

from PyQt6 import QtWidgets

from gambitpairing.gui.main_window_save_flow import UnsavedChangesPrompt
from gambitpairing.gui.ui_loader import load_ui_into, required_child


class UnsavedChangesDialog(QtWidgets.QDialog):
    """Designer-backed dialog for choosing how to handle unsaved changes."""

    def __init__(self, prompt: UnsavedChangesPrompt, parent=None):
        super().__init__(parent)
        self.setProperty("class", "UnsavedChangesDialog")
        self._selected_action = "cancel"

        load_ui_into(self, "unsaved_changes_dialog.ui")
        self._setup_ui(prompt)

    @property
    def selected_action(self) -> str:
        """Return ``save``, ``discard``, or ``cancel`` after the dialog closes."""
        return self._selected_action

    def _setup_ui(self, prompt: UnsavedChangesPrompt) -> None:
        self.setWindowTitle(prompt.title)

        self.message_label = required_child(self, QtWidgets.QLabel, "message_label")
        self.save_button = required_child(self, QtWidgets.QPushButton, "save_button")
        self.discard_button = required_child(
            self, QtWidgets.QPushButton, "discard_button"
        )
        self.cancel_button = required_child(
            self, QtWidgets.QPushButton, "cancel_button"
        )

        self.message_label.setText(prompt.message)
        self.save_button.setText(prompt.save_label)
        self.discard_button.setText(prompt.discard_label)
        self.cancel_button.setText(prompt.cancel_label)

        self.save_button.clicked.connect(lambda: self._finish("save"))
        self.discard_button.clicked.connect(lambda: self._finish("discard"))
        self.cancel_button.clicked.connect(lambda: self._finish("cancel"))

    def _finish(self, action: str) -> None:
        self._selected_action = action
        if action == "cancel":
            self.reject()
            return
        self.accept()
