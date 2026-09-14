import pytest

from gambitpairing.controllers.pairing.dutch_swiss import create_dutch_swiss_pairings
from gambitpairing.models.player import Player
from gambitpairing.exceptions import PairingTimeoutException


def test_dutch_swiss_deadline_fails_without_state_leak():
    players = [Player(f"Player {index}", 1800 - index * 10) for index in range(8)]
    for index, player in enumerate(players, start=1):
        player.pairing_number = index
        player.bsn = index
        player.is_moved_down = index % 2 == 0
        player.float_history = [index]

    original_state = {
        player.id: (player.bsn, player.is_moved_down, list(player.float_history))
        for player in players
    }

    with pytest.raises(PairingTimeoutException):
        create_dutch_swiss_pairings(
            players,
            2,
            set(),
            None,
            total_rounds=5,
            max_computation_time=1e-12,
        )
    assert {
        player.id: (player.bsn, player.is_moved_down, player.float_history)
        for player in players
    } == original_state


def test_dutch_swiss_deadline_preserves_missing_pairing_numbers():
    players = [Player(f"Player {index}", 1800 - index * 10) for index in range(4)]

    with pytest.raises(PairingTimeoutException):
        create_dutch_swiss_pairings(players, 2, set(), None, max_computation_time=1e-12)
    assert all(player.pairing_number is None for player in players)


def test_dutch_swiss_rejects_non_finite_deadline():
    players = [Player("White", 1800), Player("Black", 1700)]

    with pytest.raises(ValueError, match="finite and positive"):
        create_dutch_swiss_pairings(
            players,
            current_round=2,
            previous_matches=set(),
            get_eligible_bye_player=lambda candidates: candidates[0],
            max_computation_time=float("nan"),
        )


def test_dutch_swiss_restores_working_state_on_pairing_error(monkeypatch):
    players = [Player(f"Player {index}", 1800 - index * 10) for index in range(3)]
    for index, player in enumerate(players, start=1):
        player.pairing_number = None
        player.bsn = index
        player.is_moved_down = index % 2 == 0
        player.float_history = [index]

    original_state = {
        player.id: (
            player.pairing_number,
            player.bsn,
            player.is_moved_down,
            list(player.float_history),
        )
        for player in players
    }

    def fail_search(*args):
        raise RuntimeError("search failed")

    monkeypatch.setattr(
        "gambitpairing.controllers.pairing.strict_dutch.pair_round", fail_search
    )

    with pytest.raises(RuntimeError, match="search failed"):
        create_dutch_swiss_pairings(
            players,
            current_round=2,
            previous_matches=set(),
            get_eligible_bye_player=None,
            max_computation_time=1.0,
        )

    assert {
        player.id: (
            player.pairing_number,
            player.bsn,
            player.is_moved_down,
            player.float_history,
        )
        for player in players
    } == original_state
