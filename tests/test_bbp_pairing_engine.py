from pathlib import Path
import stat
import textwrap
from typing import Any, Iterable, Optional

import pytest

from gambitpairing.compatibility.bbp import build_bbp_pairing_trf
from gambitpairing.controllers.pairing.bbp_dutch import (
    BBPPairingEngine,
    BBPUnavailableError,
)
from gambitpairing.controllers.tournament.round import RoundController
from gambitpairing.models.enums import Colour
from gambitpairing.models.player import Player
from gambitpairing.models.tournament import PairingHistory


def _players(count: int) -> list[Player]:
    return [Player(f"Player {index}", 2000 - index) for index in range(count)]


def test_generator_uses_application_engine_discovery(monkeypatch):
    from gambitpairing.testing.rtg import BBPPairingEngine as GeneratorEngine, RTGConfig

    monkeypatch.setattr(
        BBPPairingEngine, "resolve_executable", lambda path: "/resolved/bundled-bbp"
    )
    assert (
        GeneratorEngine(RTGConfig(num_players=4, num_rounds=2)).executable
        == "/resolved/bundled-bbp"
    )


def test_explicit_missing_engine_does_not_silently_use_bundle(tmp_path):
    assert BBPPairingEngine.resolve_executable(tmp_path / "missing") is None


def _fake_bbp_executable(tmp_path: Path, output: str) -> Path:
    executable = tmp_path / "bbpPairings"
    executable.write_text(
        textwrap.dedent(f"""\
            #!/usr/bin/env python3
            print({output!r}, end="")
            """),
        encoding="utf-8",
    )
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable


def test_bbp_trf_contains_fixed_width_records_and_future_byes():
    players = _players(4)
    players[0].pairing_number = 7
    players[1].pairing_number = 9
    players[0].add_round_result(players[1], 1.0, Colour.WHITE)
    players[1].add_round_result(players[0], 0.0, Colour.BLACK)

    content = build_bbp_pairing_trf(
        players,
        total_rounds=3,
        current_round=2,
        inactive_players=[players[3]],
    )
    lines = content.splitlines()

    assert lines[:3] == ["XXC white1", "XXR 3", "240   002 0002"]
    assert all(line.startswith("001 ") and len(line) >= 84 for line in lines[3:])
    player_line = next(line for line in lines[3:] if line[4:8].strip() == "7")
    assert player_line[48:52].strip() == "2000"
    assert player_line[80:84].strip() == "1.0"
    assert "  0009 w 1" in player_line


def test_bbp_engine_maps_output_and_assigns_missing_pairing_numbers(tmp_path):
    executable = _fake_bbp_executable(tmp_path, "2\n1 3\n4 2\n")
    players = _players(4)

    pairings, bye_player = BBPPairingEngine(executable).generate_pairings(
        players,
        current_round=1,
        total_rounds=3,
    )

    assert [(white.name, black.name) for white, black in pairings] == [
        ("Player 0", "Player 2"),
        ("Player 3", "Player 1"),
    ]
    assert bye_player is None
    assert [player.pairing_number for player in players] == [1, 2, 3, 4]


def test_bbp_engine_requires_a_bye_for_an_odd_roster(tmp_path):
    executable = _fake_bbp_executable(tmp_path, "3\n1 2\n3 4\n5 0\n")
    players = _players(5)

    pairings, bye_player = BBPPairingEngine(executable).generate_pairings(
        players,
        current_round=1,
        total_rounds=3,
    )

    assert len(pairings) == 2
    assert bye_player is players[4]


def test_bbp_engine_rejects_incomplete_engine_output(tmp_path):
    executable = _fake_bbp_executable(tmp_path, "1\n1 2\n")
    players = _players(4)

    with pytest.raises(RuntimeError, match="incomplete round"):
        BBPPairingEngine(executable).generate_pairings(
            players,
            current_round=1,
            total_rounds=3,
        )


class _SpyBBPEngine:
    def __init__(self) -> None:
        self.calls: list[tuple[list[Player], dict[str, Any]]] = []

    def generate_pairings(
        self,
        active_players: Iterable[Player],
        current_round: int,
        total_rounds: int,
        all_players: Optional[Iterable[Player]] = None,
    ) -> tuple[list[tuple[Player, Player]], Optional[Player]]:
        active = list(active_players)
        self.calls.append(
            (
                active,
                {
                    "current_round": current_round,
                    "total_rounds": total_rounds,
                    "all_players": all_players,
                },
            )
        )
        return [(active[0], active[1])], active[2]


class _UnavailableBBPEngine:
    def generate_pairings(
        self,
        active_players: Iterable[Player],
        current_round: int,
        total_rounds: int,
        all_players: Optional[Iterable[Player]] = None,
    ) -> tuple[list[tuple[Player, Player]], Optional[Player]]:
        raise BBPUnavailableError("test executable is unavailable")


def test_round_controller_prefers_bbp_before_native_pairing():
    players = _players(3)
    engine = _SpyBBPEngine()
    controller = RoundController(
        "dutch_swiss",
        3,
        PairingHistory(),
        bbp_engine=engine,
    )

    pairings, bye_player = controller.create_next_round(
        {player.id: player for player in players}
    )

    assert [(white, black) for white, black in pairings] == [(players[0], players[1])]
    assert bye_player is players[2]
    assert len(engine.calls) == 1
    assert engine.calls[0][1]["total_rounds"] == 3


def test_round_controller_falls_back_to_native_when_bbp_is_unavailable():
    players = _players(4)
    controller = RoundController(
        "dutch_swiss",
        3,
        PairingHistory(),
        bbp_engine=_UnavailableBBPEngine(),
    )

    pairings, bye_player = controller.create_next_round(
        {player.id: player for player in players}
    )

    assert len(pairings) == 2
    assert bye_player is None
    assert {player.id for pair in pairings for player in pair} == {
        player.id for player in players
    }


def test_round_controller_keeps_gambit_dutch_separate_from_bbp():
    players = _players(4)
    engine = _SpyBBPEngine()
    controller = RoundController(
        "dutch_swiss",
        3,
        PairingHistory(),
        bbp_engine=engine,
        use_experimental_dutch=True,
    )

    pairings, bye_player = controller.create_next_round(
        {player.id: player for player in players}
    )

    assert len(pairings) == 2
    assert bye_player is None
    assert not engine.calls
