"""Opt-in differential tests against BBP 6.0.0 (February 2026 rules).

Set GAMBIT_REFERENCE_BBP to an independently obtained BBP executable.
These comparisons corroborate fixtures, not federation certification.
"""

import os
import random

import pytest

from gambitpairing.testing.rtg import (
    RandomTournamentGenerator,
    RTGConfig,
    RatingDistribution,
    ResultPattern,
)

from gambitpairing.controllers.pairing.bbp_dutch import BBPPairingEngine
from gambitpairing.controllers.pairing.dutch_swiss import create_dutch_swiss_pairings
from gambitpairing.controllers.tournament.replay import replay_round
from gambitpairing.models.player import Player
from gambitpairing.models.enums import Colour


@pytest.mark.skipif(
    not os.environ.get("GAMBIT_REFERENCE_BBP"), reason="Reference engine not configured"
)
@pytest.mark.parametrize("distribution", list(RatingDistribution))
@pytest.mark.parametrize("pattern", list(ResultPattern))
def test_seven_round_generator_matrix_matches_bbp(distribution, pattern):
    data = RandomTournamentGenerator(
        RTGConfig(
            num_players=16,
            num_rounds=7,
            seed=42,
            rating_distribution=distribution,
            result_pattern=pattern,
            pairing_system="dual",
            bbp_executable=os.environ["GAMBIT_REFERENCE_BBP"],
            validate_with_fpc=False,
        )
    ).generate_complete_tournament()
    assert len(data["rounds"]) == 7
    for r in data["rounds"]:
        assert {(w.id, b.id) for w, b in r["gambit_pairings"]} == {
            (w.id, b.id) for w, b in r["bbp_pairings"]
        }
        assert r["gambit_bye_player_id"] == r["bbp_bye_player_id"]


@pytest.mark.skipif(
    not os.environ.get("GAMBIT_REFERENCE_BBP"), reason="Reference engine not configured"
)
@pytest.mark.parametrize("count", [32, 64])
def test_former_round_two_timeout_matches_bbp(count):
    data = RandomTournamentGenerator(
        RTGConfig(
            num_players=count,
            num_rounds=7,
            seed=42,
            pairing_system="dual",
            bbp_executable=os.environ["GAMBIT_REFERENCE_BBP"],
            validate_with_fpc=False,
        )
    ).generate_complete_tournament()
    assert len(data["rounds"]) == 7
    for r in data["rounds"]:
        assert {(w.id, b.id) for w, b in r["gambit_pairings"]} == {
            (w.id, b.id) for w, b in r["bbp_pairings"]
        }


@pytest.mark.skipif(
    not os.environ.get("GAMBIT_REFERENCE_BBP"),
    reason="Independent BBP reference executable not configured",
)
@pytest.mark.parametrize("count", [8, 9, 10, 12, 15, 16, 20])
@pytest.mark.parametrize("seed", range(3))
@pytest.mark.parametrize("scenario", ["normal", "unplayed", "black"])
def test_same_history_matches_bbp(count, seed, scenario):
    bbp = BBPPairingEngine(
        os.environ["GAMBIT_REFERENCE_BBP"],
        initial_color="black1" if scenario == "black" else "white1",
    )
    rng = random.Random(seed)
    players = [Player(str(i), 2000 - 10 * i) for i in range(1, count + 1)]
    for number, player in enumerate(players, 1):
        player.pairing_number = number
    previous = set()

    def signature(pairings, bye):
        return sorted((w.pairing_number, b.pairing_number) for w, b in pairings), (
            bye.pairing_number if bye else None
        )

    for number in range(1, 6):
        scheduled = [players[0]] if scenario == "unplayed" and number == 2 else []
        active = [p for p in players if p not in scheduled]
        native, native_bye, _, _ = create_dutch_swiss_pairings(
            active,
            number,
            previous,
            None,
            total_rounds=5,
            max_computation_time=10,
            initial_color=Colour.BLACK if scenario == "black" else Colour.WHITE,
        )
        reference, reference_bye = bbp.generate_pairings(
            active, number, 5, all_players=players
        )
        assert signature(native, native_bye) == signature(reference, reference_bye), (
            count,
            seed,
            number,
        )
        results = [(w.id, b.id, rng.choice([0, 0.5, 1])) for w, b in reference]
        if scenario == "unplayed" and number == 1:
            w, b = reference[0]
            results[0] = (w.id, b.id, 1, 0, True)
        replay_round(
            {p.id: p for p in players},
            {
                "round_number": number,
                "pairings": [(w.id, b.id) for w, b in reference],
                "bye_player_id": reference_bye.id if reference_bye else None,
                "results": results,
                "scheduled_byes": {"half_point": [p.id for p in scheduled]},
            },
        )
        previous.update(
            frozenset((w.id, b.id))
            for i, (w, b) in enumerate(reference)
            if not (scenario == "unplayed" and number == 1 and i == 0)
        )
