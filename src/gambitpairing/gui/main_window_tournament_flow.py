"""Pure new-tournament workflow helpers for MainWindow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class NewTournamentProjection:
    name: str
    num_rounds: int
    tiebreak_order: list[str]
    pairing_system: str


def project_new_tournament_data(
    data: tuple[str, int, Sequence[str], str],
) -> NewTournamentProjection:
    name, num_rounds, tiebreak_order, pairing_system = data
    return NewTournamentProjection(
        name=name,
        num_rounds=num_rounds,
        tiebreak_order=list(tiebreak_order),
        pairing_system=pairing_system,
    )


def build_new_tournament_history(projection: NewTournamentProjection) -> str:
    return (
        f"--- New Tournament '{projection.name}' Created "
        f"(Rounds: {projection.num_rounds}, Pairing: {projection.pairing_system}) ---"
    )
