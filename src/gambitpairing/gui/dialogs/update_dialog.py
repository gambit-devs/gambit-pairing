from PyQt6 import QtCore, QtWidgets


class UpdateDownloadDialog(QtWidgets.QDialog):
    """Dialog to show download progress, completion, and errors."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Updating Gambit Pairing")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setStyleSheet(
            """
            QDialog {
                background-color: #f9fafb;
            }
            QLabel {
                font-size: 11pt;
            }
            QProgressBar {
                min-height: 28px;
                font-size: 12pt;
                text-align: center;
                border-radius: 14px;
            }
            QProgressBar::chunk {
                background-color: #2a82da;
                border-radius: 14px;
            }
            QPushButton {
                padding: 8px 16px;
                font-size: 10pt;
                border-radius: 4px;
            }
        """
        )

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        self.status_label = QtWidgets.QLabel("Connecting...", self)
        self.status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)  # <-- Fix: allow text to wrap
        self.status_label.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )  # <-- Fix: expand horizontally
        self.status_label.setStyleSheet(
            "padding-left: 12px; padding-right: 12px;"
        )  # <-- Fix: add horizontal padding
        self.layout.addWidget(self.status_label)

        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.layout.addWidget(self.progress_bar)

        self.button_box = QtWidgets.QDialogButtonBox(self)
        self.restart_btn = self.button_box.addButton(
            "Close", QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.close_btn = self.button_box.addButton(
            "Done", QtWidgets.QDialogButtonBox.ButtonRole.RejectRole
        )
        self.restart_btn.hide()
        self.close_btn.hide()
        self.layout.addWidget(self.button_box)
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

    def show_complete(self):
        self.progress_bar.setValue(100)
        self.status_label.setText(
            "Update downloaded! Please close and restart the application to apply it."
        )
        self.restart_btn.show()
        self.close_btn.show()
        self.progress_bar.setEnabled(False)

    def show_error(self, error_text: str):
        self.status_label.setText(
            f"<span style='color:#c00;'>Update failed:</span><br>{error_text}"
        )
        self.progress_bar.setEnabled(False)
        self.restart_btn.hide()
        self.close_btn.show()

    def closeEvent(self, event):
        # Only allow closing if buttons are visible (after update or error)
        if self.restart_btn.isVisible() or self.close_btn.isVisible():
            event.accept()
        else:
            event.ignore()
