from datetime import date
import os
from typing import Any, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6 import QtCore, QtWidgets
import pytest

from gambitpairing.constants import (
    DEFAULT_FIDE_TIEBREAK_ORDER,
    DEFAULT_MODE,
    TRF_FILTER,
)
from gambitpairing.controllers.tournament.session import TournamentSession as Tournament
from gambitpairing.gui import mainwindow
from gambitpairing.gui.dialogs.new_tournament_dialog import NewTournamentDialog
from gambitpairing.gui.dialogs.tournament_settings_dialoug import SettingsDialog
from gambitpairing.gui.mainwindow import GambitPairingMainWindow
from gambitpairing.models.player import create_player
from gambitpairing.models.tournament import EventDetails
from gambitpairing.representation import (
    build_trf_document,
    tournament_from_dict,
    tournament_to_dict,
    trf_problems,
)

_APP: QtWidgets.QApplication | None = None


def _app() -> QtWidgets.QApplication:
    # Keep a reference: Qt must not lose the application to garbage collection.
    global _APP
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    _APP = cast(QtWidgets.QApplication, app)
    return _APP


def _complete_event() -> EventDetails:
    return EventDetails(
        city="Chicago",
        federation="USA",
        start_date=date(2026, 10, 17),
        end_date=date(2026, 10, 18),
        chief_arbiter="Ada Lovelace",
        deputy_arbiter="Grace Hopper",
        time_control="90+30",
    )


def _tournament() -> Tournament:
    players = [
        create_player(name="Lovelace, Ada", rating=1800, fide_id=1503014),
        create_player(name="Hopper, Grace", rating=1700, fide_id=1503015),
    ]
    return Tournament("City Open", players, 5)


def test_event_details_round_trip_through_dict():
    event = _complete_event()

    assert EventDetails.from_dict(event.to_dict()) == event


def test_missing_or_unreadable_event_data_stays_unset():
    assert EventDetails.from_dict(None) == EventDetails()
    assert EventDetails.from_dict(
        {"start_date": "not a date", "federation": " usa "}
    ) == EventDetails(federation="USA")


def test_event_details_survive_saving_and_loading_a_tournament():
    tournament = _tournament()
    tournament.config.event = _complete_event()

    restored = tournament_from_dict(tournament_to_dict(tournament))

    assert restored.config.event == _complete_event()


def test_documents_saved_before_event_details_load_with_blank_event():
    data = tournament_to_dict(_tournament())
    del data["config"]["event"]

    restored = tournament_from_dict(data)

    assert restored.config.event == EventDetails()


def test_trf_header_writes_event_details_into_their_records():
    tournament = _tournament()
    tournament.config.event = _complete_event()

    lines = build_trf_document(tournament).splitlines()

    assert lines[1:5] == ["022 Chicago", "032 USA", "042 2026/10/17", "052 2026/10/18"]
    assert lines[9:12] == ["102 Ada Lovelace", "112 Grace Hopper", "122 90+30"]


def test_trf_problems_lists_what_fide_still_needs():
    tournament = _tournament()

    assert trf_problems(tournament) == [
        "City is not set (TRF record 022 is mandatory).",
        "Country is not set (TRF record 032 is mandatory).",
        "Chief arbiter is not set (TRF record 102 is mandatory).",
    ]

    tournament.config.event = _complete_event()

    assert trf_problems(tournament) == []


def test_trf_problems_flags_malformed_federation_and_reversed_dates():
    tournament = _tournament()
    tournament.config.event = EventDetails(
        city="Chicago",
        federation="US",
        chief_arbiter="Ada Lovelace",
        start_date=date(2026, 10, 18),
        end_date=date(2026, 10, 17),
    )

    problems = trf_problems(tournament)

    assert any(
        "Country 'US' is not a three-letter code" in problem for problem in problems
    )
    assert "The end date is before the start date." in problems


def test_new_tournament_dialog_keeps_event_details_on_their_own_tab():
    _app()
    dialog = NewTournamentDialog()
    tabs = dialog.setup_tabs

    assert [tabs.tabText(index) for index in range(tabs.count())] == [
        "Tournament",
        "Event details",
    ]
    dialog.event_page.city_edit.setText("  Chicago ")
    dialog.event_page.federation_edit.setText("usa")
    dialog.event_page.chief_arbiter_edit.setText("Ada Lovelace")
    dialog.event_page.start_date_edit.setDate(QtCore.QDate(2026, 10, 17))

    assert dialog.event_details() == EventDetails(
        city="Chicago",
        federation="USA",
        start_date=date(2026, 10, 17),
        chief_arbiter="Ada Lovelace",
    )
    dialog.close()


def test_new_tournament_dialog_blocks_accept_when_end_is_before_start(monkeypatch):
    _app()
    warnings: list[Any] = []
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "warning",
        lambda *args: warnings.append(args[2]),
    )
    dialog = NewTournamentDialog()
    dialog.event_page.start_date_edit.setDate(QtCore.QDate(2026, 10, 18))
    dialog.event_page.end_date_edit.setDate(QtCore.QDate(2026, 10, 17))

    dialog.accept()

    assert warnings == ["The end date is before the start date."]
    assert dialog.setup_tabs.currentWidget() is dialog.event_tab
    assert dialog.result() == 0
    dialog.close()


def test_settings_dialog_starts_from_the_tournament_event():
    _app()
    dialog = SettingsDialog(
        5,
        list(DEFAULT_FIDE_TIEBREAK_ORDER),
        DEFAULT_MODE,
        event=_complete_event(),
    )

    assert dialog.get_event_details() == _complete_event()

    dialog.event_page.city_edit.setText("Oak Park")

    assert dialog.get_event_details().city == "Oak Park"
    dialog.close()


class _FakeNewTournamentDialog:
    def __init__(self, parent=None):
        self.tournament_mode = DEFAULT_MODE

    def exec(self):
        return True

    def get_data(self):
        return (
            "City Open",
            5,
            list(DEFAULT_FIDE_TIEBREAK_ORDER),
            "dutch_swiss",
            False,
        )

    def event_details(self):
        return _complete_event()


def test_new_tournament_saves_event_details_with_the_tournament(monkeypatch):
    _app()
    window = GambitPairingMainWindow()
    monkeypatch.setattr(mainwindow, "NewTournamentDialog", _FakeNewTournamentDialog)
    monkeypatch.setattr(window, "check_save", lambda: True)

    window.prompt_new_tournament()

    assert window.tournament.config.event == _complete_event()
    window.close()


def _settings_dialog_returning(event):
    class _FakeSettingsDialog:
        def __init__(self, num_rounds, tiebreak_order, mode, parent=None, event=None):
            pass

        def configure_round_count_controls(self, *args):
            pass

        def exec(self):
            return True

        def get_settings(self):
            return 5, list(DEFAULT_FIDE_TIEBREAK_ORDER), DEFAULT_MODE

        def get_event_details(self):
            return event

    return _FakeSettingsDialog


def test_settings_change_to_event_details_is_saved_and_marks_dirty(monkeypatch):
    _app()
    window = GambitPairingMainWindow()
    window.tournament = _tournament()
    window._set_tournament_on_tabs()
    edited = EventDetails(city="Oak Park", federation="USA", chief_arbiter="Ada")
    marks: list[bool] = []
    monkeypatch.setattr(
        mainwindow, "SettingsDialog", _settings_dialog_returning(edited)
    )
    monkeypatch.setattr(window, "mark_dirty", lambda dirty=True: marks.append(dirty))

    assert window.show_settings_dialog()

    assert window.tournament.config.event == edited
    assert marks and all(marks)
    window.close()


@pytest.mark.parametrize(
    ("answer", "save_dialog_opens"),
    [
        (QtWidgets.QMessageBox.StandardButton.Cancel, False),
        (QtWidgets.QMessageBox.StandardButton.Yes, True),
    ],
)
def test_export_trf_asks_before_writing_an_incomplete_file(
    monkeypatch, answer, save_dialog_opens
):
    _app()
    window = GambitPairingMainWindow()
    questions: list[str] = []
    save_dialogs: list[tuple] = []

    def fake_question(*args):
        questions.append(args[2])
        return answer

    def fake_save_dialog(*args):
        save_dialogs.append(args)
        return "", TRF_FILTER

    monkeypatch.setattr(QtWidgets.QMessageBox, "question", fake_question)
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", fake_save_dialog)
    window.tournament = _tournament()
    window._set_tournament_on_tabs()

    window.export_trf()

    assert "City is not set" in questions[0]
    assert bool(save_dialogs) == save_dialog_opens
    window.close()
