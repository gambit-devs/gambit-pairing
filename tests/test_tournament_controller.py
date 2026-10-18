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


def test_correction_blocker_explains_why_a_round_cannot_change():
    tournament, white, black = _round_tournament()
    controller = TournamentController(tournament)
    assert controller.correction_blocker(0) == "Only completed rounds can be corrected."

    assert controller.record_results(0, [(white.id, black.id, 1.0)]).success
    assert controller.correction_blocker(0) is None

    tournament.rounds = [
        tournament.rounds[0],
        RoundData(2, [(white.id, black.id)]),
    ]
    assert controller.correction_blocker(0) == (
        "Round 2 is already paired. Undo Round 1 to change its results."
    )


def test_controller_corrects_latest_round_and_refuses_bad_corrections():
    tournament, white, black = _round_tournament()
    controller = TournamentController(tournament)
    assert controller.record_results(0, [(white.id, black.id, 1.0)]).success

    assert controller.correct_round_results(0, [(white.id, black.id, 0.0)]) == (
        True,
        None,
    )
    assert white.score == 0.0
    assert black.score == 1.0
    assert controller.current_round_index == 1
    assert tournament.rounds[0].is_completed

    success, error = controller.correct_round_results(0, [])
    assert not success
    assert error
    assert black.score == 1.0
    assert tournament.rounds[0].results[0].white_score == 0.0


def test_controller_refuses_correction_once_next_round_is_paired():
    tournament, white, black = _round_tournament()
    controller = TournamentController(tournament)
    assert controller.record_results(0, [(white.id, black.id, 1.0)]).success
    tournament.rounds = [tournament.rounds[0], RoundData(2, [(white.id, black.id)])]

    success, error = controller.correct_round_results(0, [(white.id, black.id, 0.0)])

    assert not success
    assert error == controller.correction_blocker(0)
    assert white.score == 1.0
