import os
from collections.abc import Callable
from typing import Any, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6 import QtWidgets

from gambitpairing.gui.update_workflow import UpdateWorkflowController

_APP: QtWidgets.QApplication | None = None


def _app() -> QtWidgets.QApplication:
    global _APP
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    _APP = cast(QtWidgets.QApplication, app)
    return _APP


class _FakeUpdater:
    def __init__(self) -> None:
        self.latest_version_info: dict[str, str] = {
            "tag_name": "v2.0.0",
            "body": "Release notes",
        }
        self.pending_path: str | None = None
        self.checked = False
        self.has_update = False
        self.applied_paths: list[str] = []
        self.cleaned = False

    def get_pending_update_path(self) -> str | None:
        return self.pending_path

    def apply_update(self, extracted_path: str) -> None:
        self.applied_paths.append(extracted_path)

    def cleanup_pending_update(self) -> None:
        self.cleaned = True

    def check_for_updates(self) -> bool:
        self.checked = True
        return self.has_update

    def get_latest_version(self) -> str | None:
        return self.latest_version_info.get("tag_name", "").lstrip("v")

    def get_release_notes(self) -> str | None:
        return self.latest_version_info.get("body")


class _AcceptingDialog:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs

    def exec(self) -> int:
        return 1


class _WorkflowForPromptTest(UpdateWorkflowController):
    download_started = False

    def start_update_download(self) -> None:
        self.download_started = True


def _controller(
    parent: QtWidgets.QWidget,
    updater: Any,
    *,
    statuses: list[str] | None = None,
    closed: list[bool] | None = None,
    packaged_check: Callable[[], bool] | None = None,
    question: Callable[..., object] | None = None,
    information: Callable[..., object] | None = None,
    timer_single_shot: Callable[[int, Callable[[], object]], object] | None = None,
) -> UpdateWorkflowController:
    status_messages = statuses if statuses is not None else []
    close_events = closed if closed is not None else []
    return UpdateWorkflowController(
        parent=parent,
        updater=updater,
        app_name="Gambit Pairing",
        app_version="1.0.0",
        status_callback=status_messages.append,
        close_callback=lambda: close_events.append(True),
        packaged_check=packaged_check,
        question=question,
        information=information,
        timer_single_shot=timer_single_shot,
    )


def test_pending_update_yes_applies_update_and_schedules_close():
    _app()
    parent = QtWidgets.QWidget()
    updater = _FakeUpdater()
    updater.pending_path = "pending-update"
    statuses: list[str] = []
    closed: list[bool] = []

    controller = _controller(
        parent,
        updater,
        statuses=statuses,
        closed=closed,
        question=lambda *args: QtWidgets.QMessageBox.StandardButton.Yes,
        timer_single_shot=lambda delay, callback: callback(),
    )

    assert controller.check_for_pending_update()
    assert controller.is_updating
    assert updater.applied_paths == ["pending-update"]
    assert statuses == ["Restarting to apply update..."]
    assert closed == [True]

    parent.close()


def test_pending_update_no_can_discard_downloaded_update():
    _app()
    parent = QtWidgets.QWidget()
    updater = _FakeUpdater()
    updater.pending_path = "pending-update"
    replies = [
        QtWidgets.QMessageBox.StandardButton.No,
        QtWidgets.QMessageBox.StandardButton.Yes,
    ]

    controller = _controller(
        parent,
        updater,
        question=lambda *args: replies.pop(0),
    )

    assert not controller.check_for_pending_update()
    assert updater.cleaned
    assert updater.applied_paths == []

    parent.close()


def test_manual_update_check_from_source_shows_source_install_message():
    _app()
    parent = QtWidgets.QWidget()
    updater = _FakeUpdater()
    info_messages: list[str] = []

    controller = _controller(
        parent,
        updater,
        packaged_check=lambda: False,
        information=lambda parent, title, message: info_messages.append(message),
    )

    controller.check_for_updates_manual()

    assert not updater.checked
    assert "Automatic updates are only available in packaged releases" in info_messages[0]

    parent.close()


def test_manual_update_check_without_new_release_reports_current_version():
    _app()
    parent = QtWidgets.QWidget()
    updater = _FakeUpdater()
    statuses: list[str] = []
    info_titles: list[str] = []

    controller = _controller(
        parent,
        updater,
        statuses=statuses,
        packaged_check=lambda: True,
        information=lambda parent, title, message: info_titles.append(title),
    )

    controller.check_for_updates_manual()

    assert updater.checked
    assert statuses == ["Checking for updates...", "No new updates available."]
    assert info_titles == ["Update Check"]

    parent.close()


def test_prompt_update_acceptance_starts_download_with_runtime_version_text():
    _app()
    parent = QtWidgets.QWidget()
    updater = _FakeUpdater()
    dialog_calls: list[dict[str, object]] = []

    def dialog_factory(**kwargs: object) -> _AcceptingDialog:
        dialog_calls.append(kwargs)
        return _AcceptingDialog(**kwargs)

    controller = _WorkflowForPromptTest(
        parent=parent,
        updater=cast(Any, updater),
        app_name="Gambit Pairing",
        app_version="1.0.0",
        status_callback=lambda message: None,
        close_callback=lambda: None,
        prompt_dialog_factory=cast(Any, dialog_factory),
    )

    assert controller.prompt_update()
    assert controller.download_started
    assert dialog_calls[0]["new_version"] == "2.0.0"
    assert dialog_calls[0]["current_version"] == "1.0.0"
    assert dialog_calls[0]["release_notes"] == "Release notes"

    parent.close()
