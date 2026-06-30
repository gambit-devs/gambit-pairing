"""Pure state helpers for ManualPairingDialog."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence


PairingLike = tuple[Any | None, Any | None]


@dataclass(frozen=True)
class ValidationProjection:
    text: str
    has_warnings: bool


def paired_player_count(pairings: Sequence[PairingLike]) -> int:
    return sum(1 for white, black in pairings if white and black) * 2


def incomplete_pairing_count(pairings: Sequence[PairingLike]) -> int:
    return sum(1 for white, black in pairings if not (white and black))


def accounted_player_ids(
    pairings: Sequence[PairingLike], bye_players: Sequence[Any]
) -> set[str]:
    accounted: set[str] = set()
    for white, black in pairings:
        if white:
            accounted.add(white.id)
        if black:
            accounted.add(black.id)
    for bye_player in bye_players:
        accounted.add(bye_player.id)
    return accounted


def active_unpaired_players(
    players: Iterable[Any], pairings: Sequence[PairingLike], bye_players: Sequence[Any]
) -> list[Any]:
    accounted = accounted_player_ids(pairings, bye_players)
    return [
        player
        for player in players
        if player.is_active and player.id not in accounted
    ]


def repeat_pairing_boards(
    pairings: Sequence[PairingLike], previous_matches: Iterable[Any]
) -> list[str]:
    repeat_boards: list[str] = []
    for i, (white, black) in enumerate(pairings):
        if white and black:
            for player_pair in previous_matches:
                if (
                    isinstance(player_pair, frozenset)
                    and len(player_pair) == 2
                    and white.id in player_pair
                    and black.id in player_pair
                ):
                    repeat_boards.append(str(i + 1))
                    break
    return repeat_boards


def build_stats_text(
    players: Sequence[Any], pairings: Sequence[PairingLike], bye_players: Sequence[Any]
) -> str:
    total_players = len(players)
    active_players = len([p for p in players if p.is_active])
    withdrawn_players = total_players - active_players
    paired_players = paired_player_count(pairings)
    incomplete_pairings = incomplete_pairing_count(pairings)
    bye_count = len(bye_players)
    remaining_active_players = active_players - paired_players - bye_count

    stats_text = (
        f"Players: {paired_players}/{active_players} active paired • "
        f"{remaining_active_players} active remaining • "
        f"{incomplete_pairings} incomplete boards"
    )
    if withdrawn_players > 0:
        stats_text += f" • {withdrawn_players} withdrawn"

    if bye_players:
        if len(bye_players) == 1:
            status = " (Withdrawn)" if not bye_players[0].is_active else ""
            stats_text += f" • Bye: {bye_players[0].name}{status}"
        else:
            withdrawn_byes = [p for p in bye_players if not p.is_active]
            bye_text = f" • Byes: {len(bye_players)} players"
            if withdrawn_byes:
                bye_text += f" ({len(withdrawn_byes)} withdrawn)"
            stats_text += bye_text
    return stats_text


def build_validation_projection(
    players: Sequence[Any],
    pairings: Sequence[PairingLike],
    bye_players: Sequence[Any],
    previous_matches: Iterable[Any] | None = None,
) -> ValidationProjection:
    warnings: list[str] = []

    incomplete_count = incomplete_pairing_count(pairings)
    if incomplete_count > 0:
        warnings.append(f"{incomplete_count} incomplete boards need completion")

    unpaired = active_unpaired_players(players, pairings, bye_players)
    if unpaired:
        player_names = ", ".join([p.name for p in unpaired])
        warnings.append(f"{len(unpaired)} active player(s) not paired: {player_names}")

    if previous_matches:
        repeat_boards = repeat_pairing_boards(pairings, previous_matches)
        if repeat_boards:
            warnings.append(f"Repeat pairings on boards: {', '.join(repeat_boards)}")

    if warnings:
        return ValidationProjection("⚠️ " + " • ".join(warnings), True)
    return ValidationProjection("✅ All validations passed", False)


def unresolved_active_players(
    players: Sequence[Any], pairings: Sequence[PairingLike], bye_players: Sequence[Any]
) -> set[Any]:
    accounted = accounted_player_ids(pairings, bye_players)
    unresolved: set[Any] = set()

    for white, black in pairings:
        if white and not black and white.is_active:
            unresolved.add(white)
        if black and not white and black.is_active:
            unresolved.add(black)

    for player in players:
        if player.is_active and player.id not in accounted:
            unresolved.add(player)

    return unresolved


def build_unresolved_players_message(players: Iterable[Any]) -> str:
    unresolved = list(players)
    player_names = [f"• {p.name} ({p.rating})" for p in unresolved]
    names_text = "\n".join(player_names)
    return (
        f"The following {len(unresolved)} active player(s) are not paired, "
        f"given a bye, or withdrawn:\n\n{names_text}\n\nWould you like to "
        "withdraw all these players from the tournament?"
    )
