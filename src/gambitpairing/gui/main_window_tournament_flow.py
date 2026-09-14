"""Pure new-tournament workflow helpers for MainWindow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class NewTournamentProjection:
    name: str
    num_rounds: int
    tiebreak_order: list[str]
    pairing_system: str
    use_experimental_dutch: bool = False
    tournament_mode: Optional[str] = None


def project_new_tournament_data(
    data: (
        tuple[str, int, Sequence[str], str]
        | tuple[str, int, Sequence[str], str, str]
        | tuple[str, int, Sequence[str], str, bool]
        | tuple[str, int, Sequence[str], str, bool, str]
    ),
) -> NewTournamentProjection:
    name, num_rounds, tiebreak_order, pairing_system, *extra = data
    use_experimental_dutch = False
    tournament_mode: Optional[str] = None
    if extra:
        first_extra = extra[0]
        if isinstance(first_extra, bool):
            use_experimental_dutch = first_extra
            if len(extra) > 1 and isinstance(extra[1], str):
                tournament_mode = extra[1]
        elif isinstance(first_extra, str):
            # Keep callers using the pre-checkbox five-item projection
            # compatible while the dialog now emits the explicit flag.
            tournament_mode = first_extra
    return NewTournamentProjection(
        name=name,
        num_rounds=num_rounds,
        tiebreak_order=list(tiebreak_order),
        pairing_system=pairing_system,
        use_experimental_dutch=use_experimental_dutch,
        tournament_mode=tournament_mode,
    )


def build_new_tournament_history(projection: NewTournamentProjection) -> str:
    mode_text = (
        f"Mode: {projection.tournament_mode}, "
        if projection.tournament_mode is not None
        else ""
    )
    pairing_label = projection.pairing_system
    if projection.pairing_system == "dutch_swiss":
        pairing_label = (
            "Gambit Dutch (Experimental)"
            if projection.use_experimental_dutch
            else "BBP Dutch"
        )
    return (
        f"--- New Tournament '{projection.name}' Created "
        f"({mode_text}Rounds: {projection.num_rounds}, "
        f"Pairing: {pairing_label}) ---"
    )
