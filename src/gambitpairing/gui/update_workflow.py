"""Update-check and update orchestration for the main window.

The GitHub release check decides whether a newer version exists. Accepting the
prompt then either updates in place through Velopack (platforms in
``IN_APP_UPDATE_PLATFORMS``, currently Windows) or opens the release page.
"""

from __future__ import annotations

from collections.abc import Callable
import sys
from typing import Any

from PyQt6 import QtCore, QtGui, QtWidgets

from gambitpairing.update import (
    ReleaseInfo,
    UpdateCheckError,
    VelopackUpdater,
    find_newer_release,
    in_app_update_supported,
)
from gambitpairing.utils import setup_logger

from .dialogs import UpdateDownloadDialog, UpdatePromptDialog

logger = setup_logger(__name__)

IN_APP_ACTION_TEXT = "Update and Restart"
BROWSER_ACTION_TEXT = "Open Download Page"


class UpdateDownloadWorker(QtCore.QObject):
    """Download a Velopack update in a background thread."""

    progress = QtCore.pyqtSignal(int)
    status = QtCore.pyqtSignal(str)
    done = QtCore.pyqtSignal(bool, str)  # (success, version or error message)

    def __init__(self, updater: VelopackUpdater, expected_version: str):
        super().__init__()
        self.updater = updater
        self.expected_version = expected_version

    def run(self) -> None:
        try:
            self.status.emit(f"Downloading version {self.expected_version}...")
            version = self.updater.download(
                self.expected_version, lambda value: self.progress.emit(int(value))
            )
        except Exception as error:  # Velopack raises RuntimeError subclasses
            logger.error("Update download failed: %s", error, exc_info=True)
            self.done.emit(False, str(error))
            return
        self.status.emit("Update ready to install.")
        self.done.emit(True, version)


class UpdateWorkflowController:
    """Coordinate update checks, prompts, Velopack updates and restarts."""

    def __init__(
        self,
        *,
        parent: QtWidgets.QWidget,
        app_name: str,
        app_version: str,
        status_callback: Callable[[str], object],
        close_callback: Callable[[], object],
        confirm_close: Callable[[], bool] | None = None,
        find_release: Callable[[str], ReleaseInfo | None] = find_newer_release,
        velopack_updater: VelopackUpdater | None = None,
        packaged_check: Callable[[], bool] | None = None,
        platform: str | None = None,
        open_url: Callable[[QtCore.QUrl], object] | None = None,
        information: Callable[..., Any] | None = None,
        warning: Callable[..., Any] | None = None,
        prompt_dialog_factory: Callable[..., QtWidgets.QDialog] | None = None,
        download_dialog_factory: Callable[..., UpdateDownloadDialog] | None = None,
        worker_factory: (
            Callable[[VelopackUpdater, str], UpdateDownloadWorker] | None
        ) = None,
        thread_factory: Callable[[], QtCore.QThread] | None = None,
        timer_single_shot: Callable[[int, Callable[[], object]], object] | None = None,
    ) -> None:
        self._parent = parent
        self._app_name = app_name
        self._app_version = app_version
        self._status_callback = status_callback
        self._close_callback = close_callback
        self._confirm_close = confirm_close or (lambda: True)
        self._find_release = find_release
        self.velopack_updater = velopack_updater or VelopackUpdater()
        self._packaged_check = packaged_check or (
            lambda: bool(getattr(sys, "frozen", False))
        )
        self._platform = sys.platform if platform is None else platform
        self._open_url = open_url or QtGui.QDesktopServices.openUrl
        self._information = information or QtWidgets.QMessageBox.information
        self._warning = warning or QtWidgets.QMessageBox.warning
        self._prompt_dialog_factory = prompt_dialog_factory or UpdatePromptDialog
        self._download_dialog_factory = download_dialog_factory or UpdateDownloadDialog
        self._worker_factory = worker_factory or UpdateDownloadWorker
        self._thread_factory = thread_factory or QtCore.QThread
        self._timer_single_shot = timer_single_shot or QtCore.QTimer.singleShot

        self.is_updating = False
        self.download_dialog: UpdateDownloadDialog | None = None
        self.update_thread: QtCore.QThread | None = None
        self.worker: UpdateDownloadWorker | None = None

    # -- checking --------------------------------------------------------
    def uses_in_app_update(self) -> bool:
        """Return True when accepting the prompt should update in place."""
        if not in_app_update_supported(self._platform, self._packaged_check()):
            return False
        return self.velopack_updater.is_available()

    def check_for_updates_manual(self) -> None:
        """Manually check for updates and notify the user of the result."""
        if not self._packaged_check():
            self._information(
                self._parent,
                "Update Check",
                "Update checks are only available in packaged releases.\n\n"
                "If you installed from source, please update using git or your "
                "package manager. ie: `pip install --upgrade [git-root]`",
            )
            return

        self._status_callback("Checking for updates...")
        try:
            release = self._find_release(self._app_version)
        except UpdateCheckError as error:
            self._status_callback("Update check failed.")
            self._warning(self._parent, "Update Check", str(error))
            return
        if release is not None:
            self.prompt_update(release)
            return
        self._status_callback("No new updates available.")
        self._information(
            self._parent,
            "Update Check",
            f"You are using the latest version of {self._app_name} ({self._app_version}).",
        )

    def check_for_updates_auto(self) -> None:
        """Check for updates at startup; failures are only logged."""
        if not self._packaged_check():
            return
        try:
            release = self._find_release(self._app_version)
        except UpdateCheckError as error:
            logger.warning("Automatic update check failed: %s", error)
            return
        if release is not None:
            self.prompt_update(release)

    # -- prompting -------------------------------------------------------
    def prompt_update(self, release: ReleaseInfo) -> bool:
        """Ask the user about ``release``; act on acceptance.

        Returns True when the user accepted.
        """
        in_app = self.uses_in_app_update()
        dialog = self._prompt_dialog_factory(
            new_version=release.version,
            current_version=self._app_version,
            release_notes=release.notes,
            action_text=IN_APP_ACTION_TEXT if in_app else BROWSER_ACTION_TEXT,
            parent=self._parent,
        )
        if not dialog.exec():
            return False
        if in_app:
            self.start_in_app_update(release)
        else:
            self.open_release_page(release)
        return True

    def open_release_page(self, release: ReleaseInfo) -> None:
        self._status_callback(f"Opening the download page for {release.version}...")
        if not self._open_url(QtCore.QUrl(release.page_url)):
            self._information(
                self._parent,
                "Update Available",
                f"Download version {release.version} from:\n{release.page_url}",
            )

    # -- in-app (Velopack) updates ------------------------------------------
    def start_in_app_update(self, release: ReleaseInfo) -> None:
        """Download the update in the background and show progress."""
        self._status_callback("Downloading update...")
        self.download_dialog = self._download_dialog_factory(self._parent)

        self.update_thread = self._thread_factory()
        self.worker = self._worker_factory(self.velopack_updater, release.version)
        self.worker.moveToThread(self.update_thread)

        self.update_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.download_dialog.update_progress)
        self.worker.status.connect(self.download_dialog.update_status)
        self.worker.done.connect(self.on_update_done)
        self.worker.done.connect(self.update_thread.quit)
        self.worker.done.connect(self.worker.deleteLater)
        self.update_thread.finished.connect(self.update_thread.deleteLater)

        self.update_thread.start()
        self.download_dialog.exec()

    def on_update_done(self, success: bool, message: str) -> None:
        """Show the result of the download in the progress dialog."""
        if not self.download_dialog:
            return
        if success:
            self.download_dialog.show_complete()
            self.download_dialog.restart_btn.clicked.connect(self.restart_with_update)
        else:
            self.download_dialog.show_error(message)

    def restart_with_update(self) -> None:
        """Let Velopack apply the downloaded update, then close the app."""
        if not self._confirm_close():
            self._status_callback(
                "Update downloaded; it will be installed when you restart."
            )
            return
        self.is_updating = True
        self._status_callback("Restarting to apply update...")
        try:
            self.velopack_updater.apply_and_restart()
        except Exception as error:
            self.is_updating = False
            self._warning(self._parent, "Update Failed", str(error))
            return
        self._timer_single_shot(100, self._close_callback)
