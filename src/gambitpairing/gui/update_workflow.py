"""Update-check and download orchestration for the main window."""

from __future__ import annotations

from collections.abc import Callable
import sys
from typing import Any

from PyQt6 import QtCore, QtWidgets

from gambitpairing.update import Updater, UpdateWorker

from .dialogs import UpdateDownloadDialog, UpdatePromptDialog


class UpdateWorkflowController:
    """Coordinate update checks, prompts, downloads, and restart flow."""

    def __init__(
        self,
        *,
        parent: QtWidgets.QWidget,
        updater: Updater | None,
        app_name: str,
        app_version: str,
        status_callback: Callable[[str], object],
        close_callback: Callable[[], object],
        packaged_check: Callable[[], bool] | None = None,
        question: Callable[..., Any] | None = None,
        information: Callable[..., Any] | None = None,
        warning: Callable[..., Any] | None = None,
        prompt_dialog_factory: Callable[..., QtWidgets.QDialog] | None = None,
        download_dialog_factory: Callable[..., UpdateDownloadDialog] | None = None,
        worker_factory: Callable[[Updater], UpdateWorker] | None = None,
        thread_factory: Callable[[], QtCore.QThread] | None = None,
        timer_single_shot: Callable[[int, Callable[[], object]], object] | None = None,
    ) -> None:
        self._parent = parent
        self.updater = updater
        self._app_name = app_name
        self._app_version = app_version
        self._status_callback = status_callback
        self._close_callback = close_callback
        self._packaged_check = packaged_check or (lambda: bool(getattr(sys, "frozen", False)))
        self._question = question or QtWidgets.QMessageBox.question
        self._information = information or QtWidgets.QMessageBox.information
        self._warning = warning or QtWidgets.QMessageBox.warning
        self._prompt_dialog_factory = prompt_dialog_factory or UpdatePromptDialog
        self._download_dialog_factory = download_dialog_factory or UpdateDownloadDialog
        self._worker_factory = worker_factory or UpdateWorker
        self._thread_factory = thread_factory or QtCore.QThread
        self._timer_single_shot = timer_single_shot or QtCore.QTimer.singleShot

        self.is_updating = False
        self.download_dialog: UpdateDownloadDialog | None = None
        self.update_thread: QtCore.QThread | None = None
        self.worker: UpdateWorker | None = None

    def check_for_pending_update(self) -> bool:
        """Check for a previously downloaded update and ask to install it."""
        if not self.updater:
            return False

        pending_path = self.updater.get_pending_update_path()
        if not pending_path:
            return False

        reply = self._question(
            self._parent,
            "Update Ready to Install",
            "A downloaded update is ready. This will restart the application.\n\nInstall now?",
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.restart_with_update(pending_path)
            return True

        discard_reply = self._question(
            self._parent,
            "Discard Update?",
            "Do you want to discard the downloaded update? If not, you will be asked again on the next launch.",
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
        )
        if discard_reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.updater.cleanup_pending_update()
        return False

    def check_for_updates_manual(self) -> None:
        """Manually check for updates and notify the user of the result."""
        if not self._packaged_check():
            self._information(
                self._parent,
                "Update Check",
                "Automatic updates are only available in packaged releases.\n\n"
                "If you installed from source, please update using git or your package manager. ie: `pip install --upgrade [git-root]`",
            )
            return
        if not self.updater:
            self._information(
                self._parent, "Update Check", "The update checker is not configured."
            )
            return

        self._status_callback("Checking for updates...")
        has_update = self.updater.check_for_updates()
        if has_update:
            self.prompt_update()
        else:
            self._status_callback("No new updates available.")
            self._information(
                self._parent,
                "Update Check",
                f"You are using the latest version of {self._app_name} ({self._app_version}).",
            )

    def check_for_updates_auto(self) -> None:
        """Automatically check for updates in the background."""
        if not self._packaged_check():
            return
        if not self.updater:
            return
        if self.updater.check_for_updates():
            self.prompt_update()

    def prompt_update(self) -> bool:
        """Show a dialog prompting the user to download the new version."""
        if not self.updater or not self.updater.latest_version_info:
            return False

        latest_version = self.updater.get_latest_version()
        release_notes = self.updater.get_release_notes()

        if latest_version is None or release_notes is None:
            self._warning(
                self._parent,
                "Update Error",
                "Could not retrieve complete update information.",
            )
            return False

        dialog = self._prompt_dialog_factory(
            new_version=latest_version,
            current_version=self._app_version,
            release_notes=release_notes,
            parent=self._parent,
        )

        if dialog.exec():
            self.start_update_download()
            return True
        return False

    def start_update_download(self) -> None:
        """Initiate the update download and show the progress dialog."""
        if not self.updater:
            return

        self._status_callback("Starting update download...")
        self.download_dialog = self._download_dialog_factory(self._parent)

        self.update_thread = self._thread_factory()
        self.worker = self._worker_factory(self.updater)
        self.worker.moveToThread(self.update_thread)

        self.update_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.download_dialog.update_progress)
        self.worker.status.connect(self.download_dialog.update_status)
        self.worker.done.connect(self.on_update_done)

        self.worker.finished.connect(self.update_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.update_thread.finished.connect(self.update_thread.deleteLater)

        self.worker.error.connect(self.update_thread.quit)
        self.worker.error.connect(self.worker.deleteLater)

        self.update_thread.start()
        self.download_dialog.exec()

    def on_update_done(self, success: bool, message: str) -> None:
        """Handle both successful and failed update downloads."""
        if not self.download_dialog:
            return

        if success:
            self.download_dialog.show_complete()
            self.download_dialog.restart_btn.clicked.disconnect()
            self.download_dialog.restart_btn.clicked.connect(
                lambda: self.restart_with_update(message)
            )
        else:
            self.download_dialog.show_error(message)
            self.download_dialog.close_btn.clicked.disconnect()
            self.download_dialog.close_btn.clicked.connect(self.download_dialog.close)

    def restart_with_update(self, extracted_path: str) -> None:
        """Apply an extracted update and close the window shortly after."""
        if not self.updater:
            return

        self.is_updating = True
        self._status_callback("Restarting to apply update...")
        self.updater.apply_update(extracted_path)
        self._timer_single_shot(100, self._close_callback)
