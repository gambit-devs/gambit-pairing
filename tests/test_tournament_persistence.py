import pytest

from gambitpairing.controllers.tournament.persistence import (
    TournamentGuiState,
    TournamentPersistenceService,
)
from gambitpairing.controllers.tournament.session import TournamentSession as Tournament
from gambitpairing.models.player import Player
from gambitpairing.models.tournament import RoundData
from gambitpairing.representation import TournamentDocumentError
from gambitpairing.representation.tournament import (
    tournament_from_dict,
    tournament_to_dict,
)


def test_persistence_service_round_trips_tournament_and_gui_state(tmp_path):
    service = TournamentPersistenceService()
    tournament = Tournament("City Open", [Player("Ada", 1800)], 5)
    path = tmp_path / "city-open.json"

    service.save(
        path,
        tournament,
        TournamentGuiState(
            current_round_index=2,
            last_recorded_results_data=[("white-id", "black-id", 1.0, 0.0)],
        ),
    )

    document = service.load(path)

    assert document.tournament.name == "City Open"
    assert document.tournament.num_rounds == 5
    assert [player.name for player in document.tournament.players.values()] == ["Ada"]
    assert document.gui_state.current_round_index == 0
    assert document.gui_state.last_recorded_results_data == []


def test_gui_state_round_trip_preserves_history_log(tmp_path):
    service = TournamentPersistenceService()
    tournament = Tournament("City Open", [Player("Ada", 1800)], 5)
    path = tmp_path / "city-open.json"

    service.save(
        path,
        tournament,
        TournamentGuiState(history_log=["Created tournament", "Added player"]),
    )

    document = service.load(path)

    assert document.gui_state.history_log == ["Created tournament", "Added player"]


def test_load_rejects_future_document_version():
    with pytest.raises(TournamentDocumentError, match="newer than supported"):
        tournament_from_dict(
            {
                "__version__": 2,
                "config": {"name": "City Open", "num_rounds": 1},
                "players": [],
                "rounds": [],
            }
        )


def test_load_rejects_completed_round_with_missing_result():
    white = Player("White", 1800)
    black = Player("Black", 1700)
    data = tournament_to_dict(Tournament("City Open", [white, black], 1))
    data["rounds"] = [
        {
            "round_number": 1,
            "pairings": [[white.id, black.id]],
            "results": [],
            "is_completed": True,
        }
    ]

    with pytest.raises(TournamentDocumentError, match="complete result set"):
        tournament_from_dict(data)


def test_load_rebuilds_pairing_history_from_rounds():
    white = Player("White", 1800)
    black = Player("Black", 1700)
    tournament = Tournament("City Open", [white, black], 1)
    tournament.rounds = [RoundData(1, [(white.id, black.id)])]
    data = tournament_to_dict(tournament)
    data["pairing_history"]["previous_matches"] = [["stale", "history"]]

    restored = tournament_from_dict(data)

    assert restored.pairing_history.have_played(white.id, black.id)
    assert not restored.pairing_history.have_played("stale", "history")


def test_load_rejects_finalized_and_pending_result_for_same_pairing():
    white = Player("White", 1800)
    black = Player("Black", 1700)
    data = tournament_to_dict(Tournament("City Open", [white, black], 1))
    result = {
        "white_id": white.id,
        "black_id": black.id,
        "white_score": 1.0,
    }
    data["rounds"] = [
        {
            "round_number": 1,
            "pairings": [[white.id, black.id]],
            "results": [result],
            "pending_results": [result],
            "is_completed": False,
        }
    ]

    with pytest.raises(TournamentDocumentError, match="finalized and pending"):
        tournament_from_dict(data)
