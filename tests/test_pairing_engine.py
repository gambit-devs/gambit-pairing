from gambitpairing.controllers.pairing.dutch_swiss import (
    _assign_colors_fide,
    create_dutch_swiss_pairings,
)
from gambitpairing.controllers.pairing.round_robin import create_round_robin
from gambitpairing.models.enums import Colour
from gambitpairing.models.player import Player


def _players(count: int) -> list[Player]:
    players = [Player(f"Player {idx}", 2200 - idx * 100) for idx in range(count)]
    for idx, player in enumerate(players, start=1):
        player.pairing_number = idx
    return players


def test_swiss_avoids_repeat_pairings_when_alternative_exists():
    players = _players(4)
    p1, p2, p3, p4 = players
    for player in players:
        player.score = 0.5

    previous_matches = {
        frozenset({p1.id, p3.id}),
        frozenset({p4.id, p2.id}),
    }

    pairings, bye_player, _, _ = create_dutch_swiss_pairings(
        players,
        current_round=2,
        previous_matches=previous_matches,
        get_eligible_bye_player=lambda candidates: candidates[-1],
        total_rounds=3,
    )

    assert bye_player is None
    assert len(pairings) == 2
    assert all(
        frozenset({white.id, black.id}) not in previous_matches
        for white, black in pairings
    )


def test_swiss_assigns_single_bye_for_odd_player_count():
    players = _players(5)
    expected_bye = min(players, key=lambda player: int(player.rating))

    pairings, bye_player, _, bye_player_id = create_dutch_swiss_pairings(
        players,
        current_round=1,
        previous_matches=set(),
        get_eligible_bye_player=lambda candidates: min(
            candidates, key=lambda player: int(player.rating)
        ),
        total_rounds=5,
    )

    paired_players = {player for pairing in pairings for player in pairing}

    assert bye_player is expected_bye
    assert bye_player_id == expected_bye.id
    assert expected_bye not in paired_players
    assert len(pairings) == 2


def test_swiss_color_balance_avoids_third_same_color_when_possible():
    player_with_two_whites = Player("Two Whites", 1800)
    player_with_two_blacks = Player("Two Blacks", 1700)
    player_with_two_whites.pairing_number = 1
    player_with_two_blacks.pairing_number = 2
    player_with_two_whites.color_history = [Colour.WHITE, Colour.WHITE]
    player_with_two_blacks.color_history = [Colour.BLACK, Colour.BLACK]

    white, black = _assign_colors_fide(
        player_with_two_whites, player_with_two_blacks, current_round=3
    )

    assert white is player_with_two_blacks
    assert black is player_with_two_whites


def test_round_robin_even_player_count_pairs_everyone_each_round():
    players = _players(4)

    tournament = create_round_robin(players)

    assert tournament.number_of_rounds == 3
    all_pairs: list[frozenset[str]] = []
    for matches, bye_player in tournament.get_all_pairings():
        assert bye_player is None
        assert len(matches) == 2
        for white, black in matches:
            all_pairs.append(frozenset({white.id, black.id}))

    assert len(all_pairs) == 6
    assert len(set(all_pairs)) == 6


def test_round_robin_odd_player_count_assigns_one_bye_per_round():
    players = _players(5)

    tournament = create_round_robin(players)

    bye_ids: list[str] = []
    all_pairs: list[frozenset[str]] = []
    for matches, bye_player in tournament.get_all_pairings():
        assert bye_player is not None
        bye_ids.append(bye_player.id)
        paired_ids = {player.id for match in matches for player in match}
        assert bye_player.id not in paired_ids
        assert len(matches) == 2
        for white, black in matches:
            all_pairs.append(frozenset({white.id, black.id}))

    assert tournament.number_of_rounds == 5
    assert sorted(bye_ids) == sorted(player.id for player in players)
    assert len(all_pairs) == 10
    assert len(set(all_pairs)) == 10
