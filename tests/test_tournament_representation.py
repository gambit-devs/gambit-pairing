from gambitpairing.constants import TB_MEDIAN, TB_SOLKOFF
from gambitpairing.models.player import Player
from gambitpairing.models.tournament import RoundData, Tournament
from gambitpairing.representation.tournament import (
    tournament_from_dict,
    tournament_to_dict,
)


def test_representation_preserves_config_and_state_fields():
    tournament = Tournament(
        name="City Open",
        players=[Player("Ada", 1800)],
        num_rounds=5,
        tiebreak_order=[TB_SOLKOFF, TB_MEDIAN],
        pairing_system="round_robin",
    )
    tournament.config.tournament_mode = "championship"
    tournament.config.fide_strict_mode = True
    tournament.config.tournament_over = True

    restored = tournament_from_dict(tournament_to_dict(tournament))

    assert restored.name == "City Open"
    assert restored.num_rounds == 5
    assert restored.pairing_system == "round_robin"
    assert restored.tiebreak_order == [TB_SOLKOFF, TB_MEDIAN]
    assert restored.config.tournament_mode == "championship"
    assert restored.config.fide_strict_mode is True
    assert restored.tournament_over is True


def test_clear_rounds_from_removes_later_pairings_and_history():
    p1 = Player("Ada", 1800)
    p2 = Player("Ben", 1700)
    p3 = Player("Cat", 1600)
    p4 = Player("Dee", 1500)
    tournament = Tournament("City Open", [p1, p2, p3, p4], 2)
    tournament.rounds = [
        RoundData(1, [(p1.id, p2.id)]),
        RoundData(2, [(p3.id, p4.id)]),
    ]

    tournament.clear_rounds_from(1)

    assert tournament.rounds_pairings_ids == [[(p1.id, p2.id)]]
    assert tournament.pairing_history.have_played(p1.id, p2.id)
    assert not tournament.pairing_history.have_played(p3.id, p4.id)
