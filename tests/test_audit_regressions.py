"""Behavioral regressions from the upstream/working-tree MVC audit."""

import json
import os
import subprocess
import sys

import pytest

from gambitpairing.controllers import TournamentController
from gambitpairing.controllers.tournament.pairing_job import (
    commit_pairing_document,
    generate_pairing_document,
)
from gambitpairing.controllers.tournament.replay import round_snapshot
from gambitpairing.controllers.tournament.session import TournamentSession
from gambitpairing.models.player import Player
from gambitpairing.representation import TournamentDocumentError, tournament_from_dict


def tournament():
    players = [Player(f"Player {i}", 1800 - i * 100) for i in range(4)]
    session = TournamentSession("Audit", players, 3, pairing_system="manual")
    controller = TournamentController(session)
    assert controller.set_manual_pairings(
        0, [(players[0], players[1]), (players[2], players[3])], None
    )
    return session, controller, players


def record_first(session, controller):
    assert controller.record_results(
        0, [(w, b, 1.0) for w, b in session.rounds[0].pairings]
    ).success


def test_domain_can_run_without_importing_qt():
    code = """
import sys
class NoQt:
    def find_spec(self, fullname, *args):
        if fullname.startswith(("PyQt", "PySide")):
            raise AssertionError(fullname)
sys.meta_path.insert(0, NoQt())
from gambitpairing.models.tournament import Tournament
assert not any(name.startswith("gambitpairing.controllers") for name in sys.modules)
from gambitpairing.controllers.tournament.session import TournamentSession
from gambitpairing.models.player import Player
from gambitpairing.representation import tournament_from_dict
a,b=Player("A",1800),Player("B",1700)
t=TournamentSession("Headless",[a,b],1,use_experimental_dutch=True)
t.create_pairings(1)
assert t.record_results(0,[(w,b,1.0) for w,b in t.rounds[0].pairings])
u=tournament_from_dict(t.to_dict())
u.clear_rounds_from(0)
assert all(p.score == 0 for p in u.players.values())
assert not any(name.startswith(("PyQt", "PySide")) for name in sys.modules)
"""
    subprocess.run(
        [sys.executable, "-c", code], check=True, capture_output=True, text=True
    )


def test_player_edit_preserves_history_and_membership_ids():
    session, controller, players = tournament()
    record_first(session, controller)
    original = players[0].to_dict()
    edited = session.update_player(
        players[0].id,
        {"name": "Updated", "cfc_id": 12345, "fide_id": 1234567, "score": 99},
    )
    assert edited.id == players[0].id
    assert edited.score == original["score"]
    assert edited.results == players[0].results
    assert edited.cfc_id == 12345
    assert edited.fide_id == 1234567
    assert tournament_from_dict(session.to_dict()).players[edited.id].cfc_id == 12345


def test_historical_roster_survives_later_withdrawal_and_detects_missing_assignment():
    session, _, players = tournament()
    session.set_player_active(players[0].id, False)
    document = session.to_dict()
    document["rounds"][0]["pairings"] = document["rounds"][0]["pairings"][1:]
    _, active, _, _ = round_snapshot(document["players"], document["rounds"], 1)
    assert {player.id for player in active} == set(session.players)
    assert all(player.is_active for player in active)


def test_cancel_manual_draft_restores_withdrawal():
    from gambitpairing.controllers.pairing.manual_pairing_controller import (
        ManualPairingController,
    )

    player = Player("Draft", 1800)
    draft = ManualPairingController([player])
    draft.toggle_player_withdrawal(player)
    assert not player.is_active
    draft.discard()
    assert player.is_active


def test_factory_validation_is_a_real_method():
    from gambitpairing.exceptions import InvalidPlayerDataException
    from gambitpairing.models.player.factory import PlayerFactory

    factory = PlayerFactory(strict=True)
    assert factory.create_player("Valid", rating=1800).rating == 1800
    with pytest.raises(InvalidPlayerDataException):
        factory.create_player("", rating=-10)


def test_manual_replacement_rebuilds_history_and_pending_results():
    session, controller, players = tournament()
    old = set(session.previous_matches)
    controller.set_pending_results(0, [(players[0].id, players[1].id, 1.0)])
    assert controller.set_manual_pairings(
        0, [(players[0], players[2]), (players[1], players[3])], None
    )
    assert len(session.previous_matches) == 2
    assert old.isdisjoint(session.previous_matches)
    assert session.rounds[0].pending_results == []
    before = session.to_dict()
    assert not controller.set_manual_pairings(0, [(players[0], players[0])], None)
    assert session.to_dict() == before


def test_clear_completed_round_rolls_back_scores_and_histories():
    session, controller, _ = tournament()
    record_first(session, controller)
    session.clear_rounds_from(0)
    assert session.rounds == []
    assert all(
        player.score == 0 and not player.results for player in session.players.values()
    )


def test_undo_invalidates_later_prepared_pairings():
    session, controller, players = tournament()
    record_first(session, controller)
    assert controller.set_manual_pairings(
        1, [(players[0], players[2]), (players[1], players[3])], None
    )
    assert controller.undo_last_results() == (True, None)
    assert len(session.rounds) == 1
    assert not session.rounds[0].is_completed


@pytest.mark.parametrize(
    "kind,score,code", [("full", 1.0, "U"), ("half", 0.5, "H"), ("zero", 0.0, "Z")]
)
def test_bye_semantics_record_reload_export_undo(kind, score, code):
    from gambitpairing.compatibility.bbp import _format_match

    players = [Player(f"Player {i}", 1800) for i in range(3)]
    session = TournamentSession("Byes", players, 1, pairing_system="manual")
    controller = TournamentController(session)
    assert controller.set_manual_pairings(
        0, [(players[0], players[1])], players[2], kind
    )
    restored = tournament_from_dict(session.to_dict())
    assert restored.rounds[0].bye_type == kind
    controller = TournamentController(restored)
    record_first(restored, controller)
    bye = restored.players[players[2].id]
    assert bye.score == score
    assert _format_match(
        None, bye.results[-1], None, {}, bye.outcome_types[-1]
    ).endswith(code)
    reloaded = tournament_from_dict(restored.to_dict())
    assert reloaded.players[bye.id].score == score
    assert TournamentController(reloaded).undo_last_results() == (True, None)


def test_float_history_snapshots_use_pre_round_scores():
    session, controller, players = tournament()
    record_first(session, controller)
    assert all(
        player.match_history[0] is not None
        and player.match_history[0]["opponent_score"] == 0
        for player in players
    )


def test_replay_starts_fresh_and_preserves_double_forfeits():
    session, controller, players = tournament()
    pairs = session.rounds[0].pairings
    assert controller.record_results(
        0, [(w, b, 0.0, 0.0, "double_forfeit") for w, b in pairs]
    ).success
    data = session.to_dict()
    roster, _, _, _ = round_snapshot(data["players"], data["rounds"], 1)
    assert all(player.results == [] for player in roster)
    roster, _, _, _ = round_snapshot(data["players"], data["rounds"], 2)
    assert all(
        player.score == 0 and player.outcome_types == ["double_forfeit"]
        for player in roster
    )


def test_standings_do_not_apply_unselected_head_to_head():
    session, controller, players = tournament()
    record_first(session, controller)
    players[1].score = 1.0
    players[1].rating = 3000
    session.tiebreak_order = []
    assert session.get_standings()[0] is players[1]


def test_loader_rejects_bad_history_and_rebuilds_cached_scores():
    session, controller, players = tournament()
    record_first(session, controller)
    data = session.to_dict()
    data["players"][0]["score"] = 999
    assert tournament_from_dict(data).players[players[0].id].score == 1.0
    data["players"][0]["results"] = ["bad"]
    with pytest.raises(TournamentDocumentError, match="result history"):
        tournament_from_dict(data)


def test_pairing_preparation_is_detached_and_commit_detects_changes():
    session, controller, players = tournament()
    session.pairing_system = "dutch_swiss"
    session.use_experimental_dutch = True
    expected = session.to_dict()
    result = generate_pairing_document(expected, 0)
    assert session.to_dict() == expected
    session.name = "Changed during generation"
    with pytest.raises(ValueError, match="changed"):
        commit_pairing_document(session, expected, result)


def test_settings_validate_before_mutating():
    session, _, _ = tournament()
    before = session.to_dict()
    with pytest.raises(ValueError):
        session.update_settings(6, [], "FIDE")
    assert session.to_dict() == before


def test_cfc_and_fide_identifiers_survive_creation_and_reload():
    from gambitpairing.models.player import create_player

    player = create_player(
        name="Ada Example", rating=1800, cfc_id=123456, fide_id=1234567
    )
    session = TournamentSession("IDs", [player], 3)
    reloaded = tournament_from_dict(session.to_dict()).players[player.id]
    assert reloaded.cfc_id == 123456
    assert reloaded.fide_id == 1234567
