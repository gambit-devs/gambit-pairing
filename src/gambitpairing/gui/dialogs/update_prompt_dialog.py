from PyQt6 import QtWidgets

from gambitpairing import APP_NAME
from gambitpairing.gui.ui_loader import load_ui_into, required_child


class UpdatePromptDialog(QtWidgets.QDialog):
    """A dialog to prompt the user for an update."""

    def __init__(
        self, new_version: str, current_version: str, release_notes: str, parent=None
    ):
        super().__init__(parent)
        self.setProperty("class", "UpdatePromptDialog")

        load_ui_into(self, "update_prompt_dialog.ui")

        self.title_label = required_child(self, QtWidgets.QLabel, "title_label")
        self.title_label.setText(f"A new version of {APP_NAME} is available!")

        self.version_info_label = required_child(
            self, QtWidgets.QLabel, "version_info_label"
        )
        self.version_info_label.setText(
            f"You are on version <b>{current_version}</b>. Version <b>{new_version}</b> is available."
        )

        self.release_notes_text = required_child(
            self, QtWidgets.QTextBrowser, "release_notes_text"
        )
        self.release_notes_text.setMarkdown(release_notes)

        self.button_box = required_child(
            self, QtWidgets.QDialogButtonBox, "button_box"
        )
        self.download_button = self.button_box.addButton(
            "Download", QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.later_button = self.button_box.addButton(
            "Later", QtWidgets.QDialogButtonBox.ButtonRole.RejectRole
        )

        self.download_button.setDefault(True)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
