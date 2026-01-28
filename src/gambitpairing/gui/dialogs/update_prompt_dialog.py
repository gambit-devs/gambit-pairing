from PyQt6 import QtWidgets

from gambitpairing import APP_NAME


class UpdatePromptDialog(QtWidgets.QDialog):
    """A dialog to prompt the user for an update."""

    def __init__(
        self, new_version: str, current_version: str, release_notes: str, parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("Update Available")
        self.setMinimumWidth(500)
        self.setStyleSheet(
            """
            QDialog {
                background-color: #f9fafb;
            }
            QLabel {
                font-size: 11pt;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 10pt;
            }
            QTextBrowser {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QPushButton {
                padding: 8px 16px;
                font-size: 10pt;
                border-radius: 4px;
            }
        """
        )

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # Title
        title_label = QtWidgets.QLabel(f"A new version of {APP_NAME} is available!")
        title_font = self.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        self.main_layout.addWidget(title_label)

        # Version Info
        version_info_label = QtWidgets.QLabel(
            f"You are on version <b>{current_version}</b>. Version <b>{new_version}</b> is available."
        )
        self.main_layout.addWidget(version_info_label)

        # Release Notes
        notes_group = QtWidgets.QGroupBox("Release Notes")
        notes_layout = QtWidgets.QVBoxLayout(notes_group)

        self.release_notes_text = QtWidgets.QTextBrowser()
        self.release_notes_text.setOpenExternalLinks(True)
        self.release_notes_text.setMarkdown(release_notes)
        notes_layout.addWidget(self.release_notes_text)

        self.main_layout.addWidget(notes_group)

        # Buttons
        self.button_box = QtWidgets.QDialogButtonBox()
        self.download_button = self.button_box.addButton(
            "Download", QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.later_button = self.button_box.addButton(
            "Later", QtWidgets.QDialogButtonBox.ButtonRole.RejectRole
        )

        self.download_button.setDefault(True)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.main_layout.addWidget(self.button_box)
