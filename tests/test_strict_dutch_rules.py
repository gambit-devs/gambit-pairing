import pytest

from gambitpairing.controllers.pairing.dutch_swiss import create_dutch_swiss_pairings
from gambitpairing.exceptions import (
    NoPairingAvailableException,
    PairingTimeoutException,
)
from gambitpairing.models.enums import Colour
from gambitpairing.models.player import Player
from gambitpairing.validation.fpc import create_fpc_validator


def players(count):
    result = [Player(str(i), 2000 - i) for i in range(count)]
    for number, p in enumerate(result, 1):
        p.pairing_number = number
    return result


def test_resident_exchange_is_required_and_selected():
    roster = players(4)
    previous = {frozenset((a.id, b.id)) for a in roster[:2] for b in roster[2:]}
    pairs, bye, _, _ = create_dutch_swiss_pairings(
        roster, 3, previous, None, total_rounds=5
    )
    assert [(w.pairing_number, b.pairing_number) for w, b in pairs] == [(1, 2), (3, 4)]
    assert bye is None


def test_bracket_search_backtracks_for_completion():
    roster = players(6)
    for p in roster[:3]:
        p.score = 1
    a, b, stranded = roster[:3]
    previous = {frozenset((stranded.id, p.id)) for p in roster[3:]}
    pairs, _, _, _ = create_dutch_swiss_pairings(
        roster, 4, previous, None, total_rounds=6
    )
    assert any({w.id, black.id} == {a.id, stranded.id} for w, black in pairs)
    assert len(pairs) == 3


def test_c3_applies_before_the_final_round_in_engine_and_checker():
    roster = players(2)
    for p in roster:
        p.color_history = [Colour.WHITE, Colour.WHITE]
    with pytest.raises(NoPairingAvailableException):
        create_dutch_swiss_pairings(roster, 3, set(), None, total_rounds=5)
    report = create_fpc_validator().validate_round_pairings(
        [(roster[0], roster[1])], None, 3, 5, set(), {}, players=roster
    )
    assert any(v.criterion_id == "C3" for v in report.violations)


def test_timeout_never_returns_a_repeat_even_with_legacy_flag_disabled():
    roster = players(2)
    previous = {frozenset(p.id for p in roster)}
    original = [p.to_dict() for p in roster]
    with pytest.raises(PairingTimeoutException):
        create_dutch_swiss_pairings(
            roster, 2, previous, None, fide_strict=False, max_computation_time=1e-12
        )
    assert [p.to_dict() for p in roster] == original


def test_forfeit_winner_cannot_receive_allocated_bye():
    roster = players(3)
    roster[0].add_round_result(roster[1], 1, Colour.WHITE, "forfeit_win")
    roster[0].score = 0  # Pairing score is independent of C2 eligibility.
    pairs, bye, _, _ = create_dutch_swiss_pairings(
        roster, 2, set(), None, total_rounds=3
    )
    assert bye is not roster[0]
    assert len(pairs) == 1


def test_limbo_repeat_downfloat_keeps_its_score_difference():
    from gambitpairing.testing.rtg import (
        RandomTournamentGenerator,
        RTGConfig,
        RatingDistribution,
        ResultPattern,
    )

    generator = RandomTournamentGenerator(
        RTGConfig(
            num_players=16,
            num_rounds=7,
            seed=42,
            rating_distribution=RatingDistribution.ELITE,
            result_pattern=ResultPattern.UPSET_FRIENDLY,
            pairing_system="dutch_swiss",
            validate_with_fpc=False,
        )
    )
    data = generator.generate_complete_tournament()
    pairs = {
        (w.pairing_number, b.pairing_number) for w, b in data["rounds"][4]["pairings"]
    }
    assert pairs == {
        (3, 7),
        (6, 9),
        (8, 1),
        (10, 5),
        (11, 2),
        (13, 4),
        (14, 12),
        (15, 16),
    }
