from PyQt6 import QtCore, QtWidgets

from gambitpairing.gui.gui_utils import update_widget_style
from gambitpairing.gui.ui_loader import load_ui_into, required_child


class UpdateDownloadDialog(QtWidgets.QDialog):
    """Dialog to show download progress, completion, and errors."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "UpdateDownloadDialog")

        load_ui_into(self, "update_download_dialog.ui")

        self.status_label = required_child(self, QtWidgets.QLabel, "status_label")
        self.status_label.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )

        self.progress_bar = required_child(self, QtWidgets.QProgressBar, "progress_bar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.button_box = required_child(self, QtWidgets.QDialogButtonBox, "button_box")
        self.restart_btn = self.button_box.addButton(
            "Close", QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.close_btn = self.button_box.addButton(
            "Done", QtWidgets.QDialogButtonBox.ButtonRole.RejectRole
        )
        self.restart_btn.hide()
        self.close_btn.hide()
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # Prevent closing the dialog with the 'X' button
        self.setWindowFlag(QtCore.Qt.WindowType.WindowCloseButtonHint, False)
        self.setWindowFlag(QtCore.Qt.WindowType.Dialog)

    def update_progress(self, value: int):
        self.progress_bar.setValue(value)
        if value >= 100:
            self.progress_bar.setValue(100)

    def update_status(self, text: str):
        self.status_label.setText(text)
        self.status_label.setProperty("state", "default")
        update_widget_style(self.status_label)

    def show_complete(self):
        self.progress_bar.setValue(100)
        self.status_label.setText(
            "Update downloaded! Please close and restart the application to apply it."
        )
        self.status_label.setProperty("state", "success")
        update_widget_style(self.status_label)
        self.restart_btn.show()
        self.close_btn.show()
        self.progress_bar.setEnabled(False)

    def show_error(self, error_text: str):
        self.status_label.setText(f"Update failed:\n{error_text}")
        self.status_label.setProperty("state", "error")
        update_widget_style(self.status_label)
        self.progress_bar.setEnabled(False)
        self.restart_btn.hide()
        self.close_btn.show()

    def closeEvent(self, event):
        # Only allow closing if buttons are visible (after update or error)
        if self.restart_btn.isVisible() or self.close_btn.isVisible():
            event.accept()
        else:
            event.ignore()
