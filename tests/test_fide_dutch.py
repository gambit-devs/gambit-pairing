import pytest

from gambitpairing.testing.rtg import (
    RandomTournamentGenerator,
    RatingDistribution,
    ResultPattern,
    RTGConfig,
)
from gambitpairing.validation.fpc import create_fpc_validator


def _build_round_payload(rounds):
    payload = []
    for round_data in rounds:
        payload.append(
            {
                "round_number": round_data["round_number"],
                "pairings": [
                    (white.id, black.id) for white, black in round_data["pairings"]
                ],
                "bye_player_id": round_data["bye_player_id"],
                "scheduled_byes": round_data.get("scheduled_byes", {}),
                "results": round_data["results"],
            }
        )
    return payload


def test_dutch_pairings_respect_absolute_criteria():
    config = RTGConfig(
        num_players=16,
        num_rounds=5,
        rating_distribution=RatingDistribution.FIDE,
        result_pattern=ResultPattern.REALISTIC,
        seed=123,
        retired_rate=1e9,
        half_point_bye_rate=1e9,
    )
    generator = RandomTournamentGenerator(config)
    tournament = generator.generate_complete_tournament()
    validator = create_fpc_validator()

    report = validator.validate_tournament_compliance(
        {
            "config": {"num_rounds": config.num_rounds},
            "players": tournament["players"],
            "rounds": _build_round_payload(tournament["rounds"]),
        }
    )

    absolute_violations = {
        v.criterion for v in report.violations if v.criterion in {"C1", "C2", "C3"}
    }
    assert not absolute_violations

    completion_violations = [v for v in report.violations if v.criterion == "C4"]
    assert not completion_violations


def test_no_duplicate_or_self_pairings():
    config = RTGConfig(
        num_players=20,
        num_rounds=6,
        rating_distribution=RatingDistribution.NORMAL,
        result_pattern=ResultPattern.PREDICTABLE,
        seed=321,
        retired_rate=1e9,
        half_point_bye_rate=1e9,
    )
    generator = RandomTournamentGenerator(config)
    tournament = generator.generate_complete_tournament()

    for round_data in tournament["rounds"]:
        seen = set()
        for white, black in round_data["pairings"]:
            assert white.id != black.id
            assert white.id not in seen
            assert black.id not in seen
            seen.add(white.id)
            seen.add(black.id)


def test_rtg_includes_fpc_report():
    config = RTGConfig(
        num_players=12,
        num_rounds=4,
        rating_distribution=RatingDistribution.FIDE,
        result_pattern=ResultPattern.REALISTIC,
        seed=999,
        retired_rate=1e9,
        half_point_bye_rate=1e9,
        validate_with_fpc=True,
    )
    generator = RandomTournamentGenerator(config)
    tournament = generator.generate_complete_tournament()

    assert "fpc_report" in tournament
    report = tournament["fpc_report"]
    assert "summary" in report
    assert "compliance_percentage" in report
