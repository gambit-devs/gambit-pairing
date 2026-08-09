"""Pure new-tournament workflow helpers for MainWindow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from gambitpairing.constants import DEFAULT_MODE


@dataclass(frozen=True)
class NewTournamentProjection:
    name: str
    num_rounds: int
    tiebreak_order: list[str]
    pairing_system: str
    tournament_mode: Optional[str] = None


def project_new_tournament_data(
    data: tuple[str, int, Sequence[str], str] | tuple[str, int, Sequence[str], str, str],
) -> NewTournamentProjection:
    name, num_rounds, tiebreak_order, pairing_system, *mode = data
    return NewTournamentProjection(
        name=name,
        num_rounds=num_rounds,
        tiebreak_order=list(tiebreak_order),
        pairing_system=pairing_system,
        tournament_mode=mode[0] if mode else None,
    )


def build_new_tournament_history(projection: NewTournamentProjection) -> str:
    mode_text = (
        f"Mode: {projection.tournament_mode}, "
        if projection.tournament_mode is not None
        else ""
    )
    return (
        f"--- New Tournament '{projection.name}' Created "
        f"({mode_text}Rounds: {projection.num_rounds}, "
        f"Pairing: {projection.pairing_system}) ---"
    )
