"""Editing the results of a completed round in place."""

from PyQt6 import QtWidgets
import pytest

from gambitpairing.constants import RESULT_BLACK_WIN, RESULT_WHITE_WIN
from gambitpairing.controllers.tournament.session import TournamentSession
from gambitpairing.gui.views.tournament.tournament_view import TournamentView
from gambitpairing.gui.views.tournament.tournament_view_workflow import (
    format_corrected_result_history_line,
)
from gambitpairing.models.player import Player
from gambitpairing.models.tournament import RoundData


@pytest.fixture
def app():
    """Keep one QApplication alive for the widgets each test builds."""
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _view_with_completed_round():
    players = [Player("White", 1800), Player("Black", 1700)]
    session = TournamentSession("Corrections", players, 2, pairing_system="manual")
    session.rounds = [RoundData(1, [(players[0].id, players[1].id)])]
    view = TournamentView()
    view.set_tournament(session)
    recording = view.controller.record_results(0, [(players[0].id, players[1].id, 1.0)])
    assert recording.success
    view.update_ui_state()
    return view, players


def test_corrected_result_history_line_names_round_board_and_change():
    assert (
        format_corrected_result_history_line(2, 5, "1-0", "0-1")
        == "--- Round 2 Board 5 Corrected: 1-0 -> 0-1 ---"
    )


def test_edit_results_corrects_a_completed_round_in_place(app):
    view, (white, black) = _view_with_completed_round()
    history = []
    view.history_message.connect(history.append)

    view.btn_edit_results.click()
    assert view.btn_edit_results.text() == "Done"
    assert view.pairings_table.cellWidget(0, 3).isEnabled()

    view.pairings_table.cellWidget(0, 3).setResult(RESULT_BLACK_WIN)

    assert white.score == 0.0
    assert black.score == 1.0
    assert history == [
        f"--- Round 1 Board 1 Corrected: {RESULT_WHITE_WIN} -> {RESULT_BLACK_WIN} ---"
    ]

    view.btn_edit_results.click()
    assert view.btn_edit_results.text() == "Edit Results"
    assert not view.pairings_table.cellWidget(0, 3).isEnabled()


def test_refused_correction_puts_the_board_back_to_its_saved_result(app):
    view, (white, black) = _view_with_completed_round()
    view.btn_edit_results.click()

    # A completed round must keep a result for every board, so clearing is refused.
    view.pairings_table.cellWidget(0, 3).setResult("")
    app.processEvents()

    assert view.pairings_table.cellWidget(0, 3).selectedResult() == RESULT_WHITE_WIN
    assert white.score == 1.0
    assert black.score == 0.0


def test_edit_results_is_hidden_once_the_next_round_is_paired(app):
    view, (white, black) = _view_with_completed_round()
    assert not view.btn_edit_results.isHidden()

    view.tournament.rounds = [
        view.tournament.rounds[0],
        RoundData(2, [(white.id, black.id)]),
    ]
    view.update_ui_state()

    assert view.btn_edit_results.isHidden()


def test_footer_offers_done_editing_instead_of_pairing_while_correcting(app):
    view, _players = _view_with_completed_round()
    primary = view.round_controls.btn_primary_action
    assert primary.text() == "Pair Round 2"

    view.btn_edit_results.click()

    assert primary.text() == "Done"
    assert primary.isEnabled()


def test_done_editing_returns_the_footer_to_pairing_without_pairing(app):
    view, (white, black) = _view_with_completed_round()
    view.btn_edit_results.click()

    view.round_controls.btn_primary_action.click()

    assert view._correcting_round_index is None
    assert not view.btn_edit_results.isHidden()
    assert view.round_controls.btn_primary_action.text() == "Pair Round 2"
    assert view.controller.generated_round_count == 1
    assert white.score == 1.0
