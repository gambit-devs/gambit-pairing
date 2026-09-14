from gambitpairing.controllers.tournament.session import TournamentSession as Tournament
from gambitpairing.models.player import Player
from gambitpairing.models.tournament import RoundData


def _tournament_with_pairing():
    white = Player("White", 1800)
    black = Player("Black", 1700)
    tournament = Tournament("Result Test", [white, black], 1)
    tournament.rounds = [RoundData(1, [(white.id, black.id)])]
    return tournament, white, black


def test_black_forfeit_win_scores_black_one_point():
    tournament, white, black = _tournament_with_pairing()

    assert tournament.record_results(0, [(white.id, black.id, 0.0)])

    assert white.score == 0.0
    assert black.score == 1.0
    assert tournament.rounds[0].results[0].white_score == 0.0
    assert tournament.rounds[0].results[0].black_score == 1.0


def test_double_forfeit_records_zero_zero_score():
    tournament, white, black = _tournament_with_pairing()

    assert tournament.record_results(0, [(white.id, black.id, 0.0, 0.0)])

    assert white.score == 0.0
    assert black.score == 0.0
    assert tournament.rounds[0].results[0].white_score == 0.0
    assert tournament.rounds[0].results[0].black_score == 0.0


def test_incomplete_result_batch_does_not_change_tournament_state():
    white = Player("White", 1800)
    black = Player("Black", 1700)
    extra_white = Player("Extra White", 1600)
    extra_black = Player("Extra Black", 1500)
    tournament = Tournament(
        "Result Test",
        [white, black, extra_white, extra_black],
        1,
    )
    tournament.rounds = [
        RoundData(
            1,
            [
                (white.id, black.id),
                (extra_white.id, extra_black.id),
            ],
        )
    ]

    assert not tournament.record_results(0, [(white.id, black.id, 1.0)])
    assert not tournament.rounds[0].is_completed
    assert not tournament.rounds[0].results
    assert white.score == 0.0
    assert black.score == 0.0


def test_invalid_result_does_not_leave_prior_entries_applied():
    tournament, white, black = _tournament_with_pairing()
    original_pending = [("pending-white", "pending-black", 1.0)]
    tournament.rounds[0].pending_results = [
        tournament.result_recorder._match_result_from_entry(original_pending[0])
    ]

    assert not tournament.record_results(
        0,
        [(white.id, black.id, 0.5, "not-an-outcome")],
    )
    assert white.score == 0.0
    assert black.score == 0.0
    assert not tournament.rounds[0].results
    assert tournament.rounds[0].pending_results[0].white_id == "pending-white"


def test_undo_rejects_history_mismatch_without_clearing_round():
    tournament, white, black = _tournament_with_pairing()
    assert tournament.record_results(0, [(white.id, black.id, 1.0)])
    black.opponent_ids[-1] = "different-player"

    assert not tournament.result_recorder.undo_round_results(
        tournament.rounds[0], tournament.players
    )
    assert tournament.rounds[0].is_completed
    assert len(tournament.rounds[0].results) == 1
    assert white.score == 1.0
    assert black.score == 0.0


def test_undo_removes_a_nonzero_bye_score():
    white = Player("White", 1800)
    black = Player("Black", 1700)
    bye = Player("Bye", 1600)
    tournament = Tournament("Result Test", [white, black, bye], 1)
    tournament.rounds = [RoundData(1, [(white.id, black.id)], bye_player_id=bye.id)]

    assert tournament.record_results(0, [(white.id, black.id, 1.0)])
    assert bye.score == 1.0

    assert tournament.result_recorder.undo_round_results(
        tournament.rounds[0], tournament.players
    )
    assert white.score == 0.0
    assert black.score == 0.0
    assert bye.score == 0.0
    assert not tournament.rounds[0].is_completed
