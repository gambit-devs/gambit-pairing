"""Unsaved changes confirmation dialog."""

from __future__ import annotations

from PyQt6 import QtWidgets

from gambitpairing.gui.gui_utils import get_native_icon
from gambitpairing.gui.main_window_save_flow import UnsavedChangesPrompt
from gambitpairing.gui.ui_loader import load_ui_into, required_child


class UnsavedChangesDialog(QtWidgets.QDialog):
    """Designer-backed dialog for choosing how to handle unsaved changes."""

    def __init__(self, prompt: UnsavedChangesPrompt, parent=None):
        super().__init__(parent)
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
        warning_icon_label = required_child(
            self, QtWidgets.QLabel, "warning_icon_label"
        )
        self.button_box = required_child(self, QtWidgets.QDialogButtonBox, "button_box")
        self.save_button = self.button_box.addButton(
            prompt.save_label,
            QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole,
        )
        self.discard_button = self.button_box.addButton(
            prompt.discard_label,
            QtWidgets.QDialogButtonBox.ButtonRole.DestructiveRole,
        )
        self.cancel_button = self.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        if self.cancel_button is None:
            raise RuntimeError("Unsaved changes dialog is missing its Cancel button")

        self.message_label.setText(prompt.message)
        warning_icon = get_native_icon(
            "dialog-warning", QtWidgets.QStyle.StandardPixmap.SP_MessageBoxWarning
        )
        icon_size = self.style().pixelMetric(
            QtWidgets.QStyle.PixelMetric.PM_MessageBoxIconSize, None, self
        )
        warning_icon_label.setPixmap(warning_icon.pixmap(icon_size, icon_size))
        warning_icon_label.setText("")
        warning_icon_label.setAccessibleName("Warning")
        self.cancel_button.setText(prompt.cancel_label)
        self.save_button.setDefault(True)

        self.save_button.clicked.connect(lambda: self._finish("save"))
        self.discard_button.clicked.connect(lambda: self._finish("discard"))
        self.cancel_button.clicked.connect(lambda: self._finish("cancel"))

    def _finish(self, action: str) -> None:
        self._selected_action = action
        if action == "cancel":
            self.reject()
            return
        self.accept()
