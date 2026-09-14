from gambitpairing.controllers.tournament.session import TournamentSession as Tournament
from gambitpairing.models.player import Player


def test_round_robin_rebuilds_schedule_when_active_roster_changes():
    players = [Player(f"Player {index}", 1800 - index * 100) for index in range(4)]
    tournament = Tournament("Round Robin", players, 3, pairing_system="round_robin")

    tournament.create_pairings(1)
    assert tournament.record_results(
        0, [(white, black, 0.5) for white, black in tournament.rounds[0].pairings]
    )
    first_round_pairings = {
        frozenset((white_id, black_id))
        for white_id, black_id in tournament.rounds[0].pairings
    }
    withdrawn = players[0]
    assert tournament.set_player_active(withdrawn.id, False)

    pairings, bye_player = tournament.create_pairings(2)

    paired_ids = {player.id for pairing in pairings for player in pairing}
    second_round_pairings = {
        frozenset((white.id, black.id)) for white, black in pairings
    }
    assert withdrawn.id not in paired_ids
    assert len(pairings) == 1
    assert bye_player is not None
    assert bye_player.id != withdrawn.id
    assert first_round_pairings.isdisjoint(second_round_pairings)
