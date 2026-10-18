"""FIDE TRF-16 tournament report representation."""

from __future__ import annotations

from datetime import date
from typing import Any, Iterable, Mapping, Optional, Sequence

from gambitpairing.constants import (
    DRAW_SCORE,
    OUTCOME_DOUBLE_FORFEIT,
    OUTCOME_FORFEIT_LOSS,
    OUTCOME_FORFEIT_WIN,
    WIN_SCORE,
)
from gambitpairing.models.enums import Colour

TRF_NAME_WIDTH = 33
# A round the player was not paired in. Blank records survive trailing
# whitespace being trimmed, unlike a "0000 -" record with a blank result.
UNPAIRED_ROUND_RECORD = " " * 10
TOURNAMENT_TYPES = {
    "dutch_swiss": "Individual: Swiss-System (Dutch)",
    "round_robin": "Individual: Round-Robin",
}
# TRF-16 header records, in order. Codes Gambit has no data for (city,
# federation, dates, teams, arbiters, time control, round dates) stay blank.
HEADER_CODES = (
    "012",
    "022",
    "032",
    "042",
    "052",
    "062",
    "072",
    "082",
    "092",
    "102",
    "112",
    "122",
    "132",
)


def build_trf_document(tournament: Any) -> str:
    """Serialize a tournament's completed rounds as a FIDE TRF-16 report.

    Scores come from the recorded player histories and ranks from the
    tournament's standings, so the file agrees with the Standings tab.
    """
    players = _players_in_start_order(tournament.players.values())
    numbers = {player.id: number for number, player in enumerate(players, start=1)}
    ranks = {player.id: player.standing_rank for player in tournament.get_standings()}
    rounds = tournament.rounds[: tournament.get_completed_rounds()]

    lines = _header_lines(tournament, players)
    lines.extend(
        _player_record(player, numbers, ranks.get(player.id), rounds)
        for player in players
    )
    return "\n".join(lines) + "\n"


def _players_in_start_order(players: Iterable[Any]) -> list[Any]:
    """Order players by pairing number, then as Dutch assigns missing numbers."""
    return sorted(
        players,
        key=lambda player: (
            player.pairing_number is None,
            player.pairing_number or 0,
            -player.rating,
            player.name,
            player.id,
        ),
    )


def _header_lines(tournament: Any, players: Sequence[Any]) -> list[str]:
    """Build the header in TRF-16 order, leaving unstored fields blank."""
    rated_count = sum(1 for player in players if player.rating > 0)
    tournament_type = TOURNAMENT_TYPES.get(
        tournament.pairing_system, tournament.pairing_system
    )
    values = {
        "012": _single_line(tournament.name),
        "062": str(len(players)),
        "072": str(rated_count),
        "092": tournament_type,
    }
    return [
        f"{code} {values[code]}" if code in values else code for code in HEADER_CODES
    ]


def _player_record(
    player: Any,
    numbers: Mapping[str, int],
    rank: Optional[int],
    rounds: Sequence[Any],
) -> str:
    """Build one fixed-width 001 record; column positions follow TRF-16."""
    name = _single_line(player.name)[:TRF_NAME_WIDTH]
    rating = str(player.rating) if player.rating > 0 else ""
    federation = (player.federation or "")[:3]
    fide_id = str(getattr(player, "fide_id", None) or "")
    rank_text = str(rank) if rank is not None else ""
    round_records = "".join(
        _round_record(player, index, round_data.bye_player_id, numbers)
        for index, round_data in enumerate(rounds)
    )
    return (
        f"001 {numbers[player.id]:>4} {_sex_code(player.gender)}"
        f"{_title_code(player):>3} {name:<{TRF_NAME_WIDTH}} {rating:>4} "
        f"{federation:<3} {fide_id:>11} {_birth_date(player.date_of_birth):<10} "
        f"{player.score:>4.1f} {rank_text:>4}{round_records}"
    )


def _round_record(
    player: Any,
    index: int,
    bye_player_id: Optional[str],
    numbers: Mapping[str, int],
) -> str:
    result = _history_value(player.results, index)
    if result is None:
        return UNPAIRED_ROUND_RECORD
    opponent_id = _history_value(player.opponent_ids, index)
    if opponent_id is None:
        return f"  0000 - {_bye_code(result, bye_player_id == player.id)}"

    colour = _history_value(player.color_history, index)
    colour_code = (
        "w" if colour == Colour.WHITE else "b" if colour == Colour.BLACK else "-"
    )
    outcome = _history_value(player.outcome_types, index)
    return f"  {numbers[opponent_id]:>4} {colour_code} {_game_code(result, outcome)}"


def _bye_code(result: float, pairing_allocated: bool) -> str:
    # TRF-16 cannot state a pairing-allocated bye's value, and readers score
    # "U" as a win, so a reduced pairing-allocated bye is written by score.
    if pairing_allocated and result == WIN_SCORE:
        return "U"
    if result == WIN_SCORE:
        return "F"
    if result == DRAW_SCORE:
        return "H"
    return "Z"


def _game_code(result: float, outcome: Optional[str]) -> str:
    if outcome == OUTCOME_FORFEIT_WIN:
        return "+"
    if outcome in {OUTCOME_FORFEIT_LOSS, OUTCOME_DOUBLE_FORFEIT}:
        return "-"
    if result == WIN_SCORE:
        return "1"
    if result == DRAW_SCORE:
        return "="
    return "0"


def _history_value(history: Sequence[Any], index: int) -> Any:
    return history[index] if index < len(history) else None


def _sex_code(gender: Optional[str]) -> str:
    return {"M": "m", "F": "w"}.get(str(gender or "")[:1].upper(), " ")


def _title_code(player: Any) -> str:
    return str(getattr(player, "fide_title", None) or "")[:3]


def _birth_date(value: Any) -> str:
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value)
        except ValueError:
            return ""
    return value.strftime("%Y/%m/%d") if isinstance(value, date) else ""


def _single_line(text: str) -> str:
    return " ".join(str(text).split())
