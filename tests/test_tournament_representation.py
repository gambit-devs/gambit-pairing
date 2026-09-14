from gambitpairing.constants import TB_MEDIAN, TB_SOLKOFF
from gambitpairing.controllers.tournament.session import TournamentSession as Tournament
from gambitpairing.models.player import Player
from gambitpairing.models.tournament import RoundData
from gambitpairing.models.tournament.tournament_config import TournamentConfig
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


def test_dutch_engine_selection_round_trips_and_legacy_ids_migrate():
    tournament = Tournament(
        name="Experimental Open",
        players=[Player("Ada", 1800)],
        num_rounds=5,
        use_experimental_dutch=True,
    )

    restored = tournament_from_dict(tournament_to_dict(tournament))

    assert restored.pairing_system == "dutch_swiss"
    assert restored.use_experimental_dutch is True
    assert restored.round_controller.use_experimental_dutch is True

    legacy_bbp = TournamentConfig.from_dict(
        {"name": "BBP Open", "num_rounds": 5, "pairing_system": "bbp_dutch"}
    )
    assert legacy_bbp.pairing_system == "dutch_swiss"
    assert legacy_bbp.use_experimental_dutch is False

    legacy_native = TournamentConfig.from_dict(
        {"name": "Native Open", "num_rounds": 5, "pairing_system": "dutch_swiss"}
    )
    assert legacy_native.pairing_system == "dutch_swiss"
    assert legacy_native.use_experimental_dutch is True


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
