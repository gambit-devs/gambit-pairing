import pytest

from gambitpairing.controllers.pairing.dutch_swiss import create_dutch_swiss_pairings
from gambitpairing.models.player import Player


def test_dutch_swiss_deadline_returns_complete_pairings_without_state_leak():
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

    pairings, bye_player, pairing_ids, bye_id = create_dutch_swiss_pairings(
        players,
        current_round=2,
        previous_matches=set(),
        get_eligible_bye_player=lambda candidates: candidates[0],
        total_rounds=5,
        max_computation_time=1e-6,
    )

    paired_ids = {player.id for pairing in pairings for player in pairing}
    assert bye_player is None
    assert bye_id is None
    assert len(pairings) == 4
    assert paired_ids == {player.id for player in players}
    assert len(pairing_ids) == len(pairings)
    assert all(white.id != black.id for white, black in pairings)
    assert {
        player.id: (player.bsn, player.is_moved_down, player.float_history)
        for player in players
    } == original_state


def test_dutch_swiss_deadline_assigns_missing_pairing_numbers():
    players = [Player(f"Player {index}", 1800 - index * 10) for index in range(4)]

    pairings, bye_player, _pairing_ids, bye_id = create_dutch_swiss_pairings(
        players,
        current_round=2,
        previous_matches=set(),
        get_eligible_bye_player=lambda candidates: candidates[0],
        total_rounds=5,
        max_computation_time=1e-6,
    )

    assert bye_player is None
    assert bye_id is None
    assert len(pairings) == 2
    assert all(player.pairing_number is not None for player in players)


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


def test_dutch_swiss_restores_working_state_on_pairing_error():
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

    def fail_bye_selection(_players):
        raise RuntimeError("bye selection failed")

    with pytest.raises(RuntimeError, match="bye selection failed"):
        create_dutch_swiss_pairings(
            players,
            current_round=2,
            previous_matches=set(),
            get_eligible_bye_player=fail_bye_selection,
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
