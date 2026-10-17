from collections.abc import Callable
import os
from typing import Any, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6 import QtCore, QtWidgets

from gambitpairing.gui.update_workflow import (
    BROWSER_ACTION_TEXT,
    IN_APP_ACTION_TEXT,
    UpdateWorkflowController,
)
from gambitpairing.update import ReleaseInfo, UpdateCheckError

_APP: QtWidgets.QApplication | None = None

RELEASE = ReleaseInfo(
    version="2.0.0",
    tag="v2.0.0",
    notes="Release notes",
    page_url="https://github.com/gambit-devs/gambit-pairing/releases/tag/v2.0.0",
)


def _app() -> QtWidgets.QApplication:
    global _APP
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    _APP = cast(QtWidgets.QApplication, app)
    return _APP


class _FakeVelopack:
    def __init__(self, available: bool = True) -> None:
        self.available = available
        self.applied = 0

    def is_available(self) -> bool:
        return self.available

    def apply_and_restart(self) -> None:
        self.applied += 1


class _Dialog:
    def __init__(self, accept: bool, calls: list[dict[str, object]], **kwargs):
        self.accept = accept
        calls.append(kwargs)

    def exec(self) -> int:
        return int(self.accept)


class _Recorder(UpdateWorkflowController):
    started: list[ReleaseInfo]

    def start_in_app_update(self, release: ReleaseInfo) -> None:
        self.started.append(release)


def _controller(
    *,
    platform: str = "win32",
    packaged: bool = True,
    velopack: _FakeVelopack | None = None,
    find_release: Callable[[str], ReleaseInfo | None] = lambda current: RELEASE,
    accept: bool = True,
    statuses: list[str] | None = None,
    infos: list[tuple[str, str]] | None = None,
    warnings: list[tuple[str, str]] | None = None,
    opened: list[str] | None = None,
    dialog_calls: list[dict[str, object]] | None = None,
    confirm_close: Callable[[], bool] = lambda: True,
    closed: list[bool] | None = None,
) -> _Recorder:
    _app()
    statuses = statuses if statuses is not None else []
    infos = infos if infos is not None else []
    warnings = warnings if warnings is not None else []
    opened = opened if opened is not None else []
    dialog_calls = dialog_calls if dialog_calls is not None else []
    closed = closed if closed is not None else []

    def open_url(url: QtCore.QUrl) -> bool:
        opened.append(url.toString())
        return True

    controller = _Recorder(
        parent=QtWidgets.QWidget(),
        app_name="Gambit Pairing",
        app_version="1.0.0",
        status_callback=statuses.append,
        close_callback=lambda: closed.append(True),
        confirm_close=confirm_close,
        find_release=find_release,
        velopack_updater=cast(Any, velopack or _FakeVelopack()),
        packaged_check=lambda: packaged,
        platform=platform,
        open_url=open_url,
        information=lambda parent, title, text: infos.append((title, text)),
        warning=lambda parent, title, text: warnings.append((title, text)),
        prompt_dialog_factory=cast(
            Any, lambda **kwargs: _Dialog(accept, dialog_calls, **kwargs)
        ),
        timer_single_shot=lambda delay, callback: callback(),
    )
    controller.started = []
    return controller


def test_windows_packaged_build_updates_in_app():
    calls: list[dict[str, object]] = []
    opened: list[str] = []
    controller = _controller(dialog_calls=calls, opened=opened)

    assert controller.prompt_update(RELEASE)

    assert controller.started == [RELEASE]
    assert opened == []
    assert calls[0]["action_text"] == IN_APP_ACTION_TEXT
    assert calls[0]["new_version"] == "2.0.0"
    assert calls[0]["current_version"] == "1.0.0"
    assert calls[0]["release_notes"] == "Release notes"


def test_macos_and_linux_open_the_release_page():
    for platform in ("darwin", "linux"):
        calls: list[dict[str, object]] = []
        opened: list[str] = []
        controller = _controller(platform=platform, dialog_calls=calls, opened=opened)

        assert controller.prompt_update(RELEASE)

        assert controller.started == []
        assert opened == [RELEASE.page_url]
        assert calls[0]["action_text"] == BROWSER_ACTION_TEXT


def test_windows_without_velopack_install_falls_back_to_release_page():
    opened: list[str] = []
    controller = _controller(velopack=_FakeVelopack(available=False), opened=opened)

    assert controller.prompt_update(RELEASE)

    assert controller.started == []
    assert opened == [RELEASE.page_url]


def test_declining_the_prompt_does_nothing():
    opened: list[str] = []
    controller = _controller(accept=False, opened=opened)

    assert not controller.prompt_update(RELEASE)
    assert controller.started == [] and opened == []


def test_manual_check_from_source_shows_source_install_message():
    checked: list[str] = []
    infos: list[tuple[str, str]] = []
    controller = _controller(
        packaged=False,
        infos=infos,
        find_release=lambda current: checked.append(current) or RELEASE,
    )

    controller.check_for_updates_manual()

    assert checked == []
    assert "only available in packaged releases" in infos[0][1]


def test_manual_check_without_new_release_reports_current_version():
    statuses: list[str] = []
    infos: list[tuple[str, str]] = []
    controller = _controller(
        statuses=statuses, infos=infos, find_release=lambda current: None
    )

    controller.check_for_updates_manual()

    assert statuses == ["Checking for updates...", "No new updates available."]
    assert infos[0][0] == "Update Check"
    assert "1.0.0" in infos[0][1]


def test_manual_check_reports_errors_and_auto_check_stays_quiet():
    def failing(current: str) -> ReleaseInfo | None:
        raise UpdateCheckError("offline")

    warnings: list[tuple[str, str]] = []
    controller = _controller(warnings=warnings, find_release=failing)
    controller.check_for_updates_manual()
    assert warnings == [("Update Check", "offline")]

    quiet: list[tuple[str, str]] = []
    controller = _controller(warnings=quiet, find_release=failing)
    controller.check_for_updates_auto()
    assert quiet == []


def test_auto_check_prompts_only_for_packaged_builds():
    calls: list[dict[str, object]] = []
    _controller(packaged=False, dialog_calls=calls).check_for_updates_auto()
    assert calls == []
    _controller(dialog_calls=calls).check_for_updates_auto()
    assert len(calls) == 1


def test_restart_applies_update_and_closes_after_save_check():
    velopack = _FakeVelopack()
    closed: list[bool] = []
    controller = _controller(velopack=velopack, closed=closed)

    controller.restart_with_update()

    assert velopack.applied == 1
    assert controller.is_updating
    assert closed == [True]


def test_restart_is_cancelled_when_user_keeps_unsaved_work():
    velopack = _FakeVelopack()
    closed: list[bool] = []
    controller = _controller(
        velopack=velopack, closed=closed, confirm_close=lambda: False
    )

    controller.restart_with_update()

    assert velopack.applied == 0
    assert not controller.is_updating
    assert closed == []
