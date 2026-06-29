from gambitpairing.models.player import Player
from gambitpairing.models.tournament import RoundData, Tournament


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
