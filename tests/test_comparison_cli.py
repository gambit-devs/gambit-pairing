from gambitpairing.comparison.cli import (
    _build_round_snapshot,
    _create_fresh_player,
)
from gambitpairing.models.enums import Colour
from gambitpairing.models.player import Player


def test_fresh_comparison_player_preserves_identity_and_clears_derived_state():
    source = Player("Ada", 1800)
    source.pairing_number = 7
    source.club = "City Club"
    source.add_round_result(Player("Opponent", 1700), 1.0, Colour.WHITE)

    fresh = _create_fresh_player(source)

    assert fresh.id == source.id
    assert fresh.name == source.name
    assert fresh.rating == source.rating
    assert fresh.pairing_number == 7
    assert fresh.club == "City Club"
    assert fresh.score == 0.0
    assert fresh.results == []
    assert fresh.opponent_ids == []
    assert fresh.color_history == []
    assert fresh.outcome_types == []
    assert fresh.running_scores == []
    assert fresh.match_history == []
    assert not hasattr(fresh, "points")


def test_round_snapshot_rebuilds_history_from_prior_rounds():
    white = Player("White", 1800)
    black = Player("Black", 1700)
    players = [white.to_dict(), black.to_dict()]
    rounds = [
        {
            "round_number": 1,
            "pairings": [[white.id, black.id]],
            "results": [
                {
                    "white_id": white.id,
                    "black_id": black.id,
                    "white_score": 1.0,
                }
            ],
        }
    ]

    snapshot_players, active_players, previous_matches, bye_history = (
        _build_round_snapshot(players, rounds, 2)
    )

    assert {player.id for player in snapshot_players} == {white.id, black.id}
    assert {player.id for player in active_players} == {white.id, black.id}
    assert frozenset((white.id, black.id)) in previous_matches
    assert bye_history == {}


def test_round_snapshot_preserves_double_forfeit_score():
    white = Player("White", 1800)
    black = Player("Black", 1700)
    players = [white.to_dict(), black.to_dict()]
    rounds = [
        {
            "round_number": 1,
            "pairings": [[white.id, black.id]],
            "results": [
                {
                    "white_id": white.id,
                    "black_id": black.id,
                    "white_score": 0.0,
                    "outcome_type": "double_forfeit",
                }
            ],
        }
    ]

    snapshot_players, _active_players, _previous_matches, _bye_history = (
        _build_round_snapshot(players, rounds, 2)
    )

    assert {player.score for player in snapshot_players} == {0.0}
