import os
from typing import Any, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6 import QtWidgets

from gambitpairing.constants import TRF_FILTER
from gambitpairing.controllers.tournament.session import TournamentSession as Tournament
from gambitpairing.gui.main_window_state import build_main_window_ui_state
from gambitpairing.gui.mainwindow import GambitPairingMainWindow
from gambitpairing.models.player import Player

_APP: QtWidgets.QApplication | None = None


def _app() -> QtWidgets.QApplication:
    global _APP
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    _APP = cast(QtWidgets.QApplication, app)
    return _APP


def _file_menu_actions(window):
    menu_bar = window.findChild(QtWidgets.QMenuBar, "menubar")
    file_menu = next(
        action.menu() for action in menu_bar.actions() if action.text() == "&File"
    )
    return file_menu.actions()


def _record_messages(monkeypatch):
    messages = []
    for name in ("information", "critical"):
        monkeypatch.setattr(
            QtWidgets.QMessageBox,
            name,
            lambda *args, _name=name: messages.append((_name, args[1], args[2])),
        )
    return messages


def test_export_trf_action_follows_export_standings_in_file_menu():
    _app()
    window = GambitPairingMainWindow()

    actions = _file_menu_actions(window)
    index = actions.index(window.export_standings_action)

    assert actions[index + 1] is window.export_trf_action
    assert window.export_trf_action.text() == "Export &TRF..."
    assert not window.export_trf_action.isEnabled()

    window.tournament = Tournament("City Open", [], 5)
    window._set_tournament_on_tabs()
    assert window.export_trf_action.isEnabled()

    window.close()


def test_export_trf_ui_state_requires_a_tournament():
    common: dict[str, Any] = dict(
        current_round_index=0,
        last_recorded_results_data=[],
        dirty=False,
        current_filepath=None,
        app_name="Gambit Pairing",
    )

    assert not build_main_window_ui_state(tournament=None, **common).can_export_trf
    assert build_main_window_ui_state(
        tournament=Tournament("City Open", [], 5), **common
    ).can_export_trf


def test_export_trf_without_tournament_reports_and_skips_dialog(monkeypatch):
    _app()
    window = GambitPairingMainWindow()
    messages = _record_messages(monkeypatch)
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getSaveFileName",
        lambda *args: (_ for _ in ()).throw(AssertionError("dialog opened")),
    )

    window.export_trf()

    assert messages == [("information", "Export Error", "No tournament data.")]
    window.close()


def test_export_trf_writes_selected_file(monkeypatch, tmp_path):
    _app()
    window = GambitPairingMainWindow()
    messages = _record_messages(monkeypatch)
    target = tmp_path / "city-open.trf"
    dialog_calls = []

    def fake_save_dialog(*args):
        dialog_calls.append(args[1:])
        return str(target), TRF_FILTER

    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", fake_save_dialog)
    window.tournament = Tournament(
        "City Open", [Player("Ada", 1500), Player("Bert", 1400)], 5
    )
    window._set_tournament_on_tabs()

    window.export_trf_action.trigger()

    assert dialog_calls == [("Export TRF", "", "TRF Files (*.trf)")]
    lines = target.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "012 City Open"
    assert [line[14:47].rstrip() for line in lines if line.startswith("001")] == [
        "Ada",
        "Bert",
    ]
    assert messages == [
        ("information", "Export Successful", f"Tournament exported to {target}")
    ]
    window.close()


def test_export_trf_cancelled_dialog_writes_nothing(monkeypatch, tmp_path):
    _app()
    window = GambitPairingMainWindow()
    messages = _record_messages(monkeypatch)
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", lambda *args: ("", "")
    )
    window.tournament = Tournament("City Open", [], 5)

    window.export_trf()

    assert messages == []
    assert list(tmp_path.iterdir()) == []
    window.close()


def test_export_trf_write_failure_shows_error(monkeypatch, tmp_path):
    _app()
    window = GambitPairingMainWindow()
    messages = _record_messages(monkeypatch)
    target = tmp_path / "missing-directory" / "city-open.trf"
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getSaveFileName",
        lambda *args: (str(target), TRF_FILTER),
    )
    window.tournament = Tournament("City Open", [], 5)

    window.export_trf()

    assert [(kind, title) for kind, title, _message in messages] == [
        ("critical", "Export Error")
    ]
    assert messages[0][2].startswith("Could not save TRF file:\n")
    assert not target.exists()
    window.close()
