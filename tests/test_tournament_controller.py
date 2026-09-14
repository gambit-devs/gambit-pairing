from gambitpairing.controllers import TournamentController
from gambitpairing.controllers.tournament.session import TournamentSession as Tournament
from gambitpairing.models.player import Player
from gambitpairing.models.tournament import RoundData


def _round_tournament() -> tuple[Tournament, Player, Player]:
    white = Player("White", 1800)
    black = Player("Black", 1700)
    tournament = Tournament("Controller Test", [white, black], 1)
    tournament.rounds = [RoundData(1, [(white.id, black.id)])]
    return tournament, white, black


def test_round_controller_owns_pending_results_and_undo():
    tournament, white, black = _round_tournament()
    controller = TournamentController(tournament)

    assert controller.set_pending_results(0, [(white.id, black.id, 1.0)])
    assert len(tournament.rounds[0].pending_results) == 1
    assert white.score == 0.0
    assert black.score == 0.0

    recording = controller.record_results(0, [(white.id, black.id, 1.0)])
    assert recording.success
    assert controller.can_undo()
    assert tournament.rounds[0].is_completed

    undone, error = controller.undo_last_results()
    assert undone, error
    assert controller.current_round_index == 0
    assert not tournament.rounds[0].is_completed
    assert not tournament.rounds[0].results
    assert white.score == 0.0
    assert black.score == 0.0


def test_round_controller_accepts_valid_player_counts():
    tournament, _, _ = _round_tournament()
    controller = TournamentController(tournament)

    validation = controller.validate_minimum_players()

    assert validation.valid
    assert not validation.needs_confirmation
