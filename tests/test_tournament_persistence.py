from gambitpairing.controllers.tournament.persistence import (
    TournamentGuiState,
    TournamentPersistenceService,
)
from gambitpairing.models.player import Player
from gambitpairing.models.tournament import Tournament


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
    assert document.gui_state.current_round_index == 2
    assert document.gui_state.last_recorded_results_data == [
        ["white-id", "black-id", 1.0, 0.0]
    ]
