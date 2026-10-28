"""Dutch pairing rules shared by the BBP-compatible and strict Dutch searches.

These helpers depend on nothing else in the Dutch modules, so both
``dutch_swiss`` and ``strict_dutch`` import them without an import cycle.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Iterable, Optional, Set, Tuple

from gambitpairing.constants import BYE_SCORE
from gambitpairing.models.enums import Colour
from gambitpairing.models.player import Player

WHITE = Colour.WHITE


def _pairing_number(player: Player) -> int:
    return player.pairing_number or 0


def _has_participated_in_pairing(player: Player) -> bool:
    """Whether the player was paired, or given the pairing-allocated bye.

    Scheduled half/zero-point byes and skipped rounds are not participation.
    """
    results = player.results
    return any(
        opponent_id is not None or (i < len(results) and results[i] == BYE_SCORE)
        for i, opponent_id in enumerate(player.opponent_ids)
    )


def effective_pairing_numbers(
    active_players: Iterable[Player], roster: Iterable[Player]
) -> Dict[str, int]:
    """Number players for Article 5.2.5 as if late entries had not arrived.

    C.04.2 Article 2.4 gives a late entry a TPN only once they arrive, so a
    player who has never been paired and is absent this round does not yet
    occupy a TPN. The remaining roster keeps TPN order (as BBP does).
    """
    active_ids = {player.id for player in active_players}
    counted = sorted(
        (
            player
            for player in roster
            if player.id in active_ids or _has_participated_in_pairing(player)
        ),
        key=_pairing_number,
    )
    return {player.id: number for number, player in enumerate(counted, 1)}


def _is_topscorer(player: Player, current_round: int, total_rounds: int) -> bool:
    """FIDE Article 1.7: Topscorers are players who have a score of over 50% of the maximum possible score WHEN PAIRING THE FINAL ROUND.

    Notes
    -----
    This function should only return True for the final round.
    """
    # FIDE Rule: Topscorer status only matters when pairing the final round
    if current_round != total_rounds or total_rounds <= 0:
        return False

    # Maximum possible score up to current round is (current_round - 1)
    # since we're pairing for the current round, not after it
    max_possible_score = current_round - 1
    return player.score > (max_possible_score * 0.5)


class FloatType(Enum):
    """Types of floaters based on C++ implementation"""

    FLOAT_DOWN = 1
    FLOAT_UP = 2
    FLOAT_NONE = 3


def _meets_absolute_criteria(
    p1: Player,
    p2: Player,
    previous_matches: Set[frozenset],
    current_round: int = 0,
    total_rounds: int = 0,
) -> bool:
    """C1 and C3; only final-round topscorers receive the C3 exception."""
    # C1: Players must not have played before (absolute requirement)
    if frozenset({p1.id, p2.id}) in previous_matches:
        return False

    return (
        _is_topscorer(p1, current_round, total_rounds)
        or _is_topscorer(p2, current_round, total_rounds)
        or not (
            _has_absolute_color_preference(p1) and _has_absolute_color_preference(p2)
        )
        or _get_color_preference(p1) != _get_color_preference(p2)
    )


def _assign_colors_fide(
    p1: Player,
    p2: Player,
    current_round: int,
    initial_color: str = WHITE,
    pairing_numbers: Optional[Dict[str, int]] = None,
) -> Tuple[Player, Player]:
    """
    Assign colors according to FIDE Article 5 rules (descending priority).
    Returns (white_player, black_player)

    FIDE Article 5.2 Priority Order:
    5.2.1: Grant both colour preferences (if compatible)
    5.2.2: Grant the stronger colour preference (absolute > strong > mild)
    5.2.3: Alternate colours to most recent time when one had W and other B
    5.2.4: Grant colour preference of higher ranked player
    5.2.5: Use pairing number parity with initial-colour
    """
    pref1 = _get_color_preference(p1)
    pref2 = _get_color_preference(p2)
    abs1 = _has_absolute_color_preference(p1)
    abs2 = _has_absolute_color_preference(p2)
    strong1 = _has_strong_color_preference(p1)
    strong2 = _has_strong_color_preference(p2)

    if pref1 and not pref2:
        return (p1, p2) if pref1 == WHITE else (p2, p1)
    if pref2 and not pref1:
        return (p2, p1) if pref2 == WHITE else (p1, p2)

    # 5.2.1: Grant both colour preferences (if compatible)
    if pref1 and pref2 and pref1 != pref2:
        return (p1, p2) if pref1 == Colour.WHITE else (p2, p1)

    # 5.2.2: Grant the stronger colour preference
    # Priority hierarchy: absolute > strong > mild

    # Both absolute: grant to player with wider color difference (FIDE rule for topscorers)
    if abs1 and abs2:
        balance1 = _get_color_imbalance(p1)
        balance2 = _get_color_imbalance(p2)
        # Grant preference to player with wider imbalance
        if abs(balance1) > abs(balance2):
            return (p1, p2) if pref1 == Colour.WHITE else (p2, p1)
        elif abs(balance2) > abs(balance1):
            return (p2, p1) if pref2 == Colour.WHITE else (p1, p2)
        # If equal imbalances, both are absolute preferences that conflict
        # This pairing should have been avoided by absolute criteria check
        # Fall through to next rule

    # One absolute vs non-absolute: absolute wins
    elif abs1 and not abs2:
        return (p1, p2) if pref1 == Colour.WHITE else (p2, p1)
    elif abs2 and not abs1:
        return (p2, p1) if pref2 == Colour.WHITE else (p1, p2)

    # Both strong (non-absolute): if different preferences, grant both
    elif strong1 and strong2:
        if pref1 and pref2 and pref1 != pref2:
            return (p1, p2) if pref1 == Colour.WHITE else (p2, p1)
        # If same strong preferences, this is a conflict - fall through

    # One strong vs mild/none: strong wins
    elif strong1 and not strong2 and not abs2:
        return (p1, p2) if pref1 == Colour.WHITE else (p2, p1)
    elif strong2 and not strong1 and not abs1:
        return (p2, p1) if pref2 == Colour.WHITE else (p1, p2)

    # 5.2.3: Alternate colours to most recent time when one had W and other B
    recent_alternating_round = _find_most_recent_alternating_colors(p1, p2)
    if recent_alternating_round is not None:
        # Get colors from that round and alternate them
        p1_colors = _played_colors(p1)
        p2_colors = _played_colors(p2)

        if recent_alternating_round < len(p1_colors):
            p1_color_then = p1_colors[recent_alternating_round]
            # Alternate: if p1 had W then, give p1 B now (so p2 gets W)
            return (p2, p1) if p1_color_then == Colour.WHITE else (p1, p2)

    # 5.2.4: Grant colour preference of higher ranked player
    # Higher rank = better score, then better rating, then lower pairing number
    if (-p1.score, p1.pairing_number) < (
        -p2.score,
        p2.pairing_number,
    ):
        higher_ranked = p1
        lower_ranked = p2
    else:
        higher_ranked = p2
        lower_ranked = p1

    higher_pref = _get_color_preference(higher_ranked)
    if higher_pref:
        return (
            (higher_ranked, lower_ranked)
            if higher_pref == Colour.WHITE
            else (lower_ranked, higher_ranked)
        )

    # 5.2.5: Use pairing number parity with initial-colour
    # Higher ranked player: odd pairing number = initial-colour (W), even = opposite (B)
    number = (pairing_numbers or {}).get(
        higher_ranked.id, _pairing_number(higher_ranked)
    )
    if number % 2 == 1:
        return (
            (higher_ranked, lower_ranked)
            if initial_color == WHITE
            else (lower_ranked, higher_ranked)
        )
    else:
        return (
            (lower_ranked, higher_ranked)
            if initial_color == WHITE
            else (higher_ranked, lower_ranked)
        )


def _find_most_recent_alternating_colors(p1: Player, p2: Player) -> Optional[int]:
    """
    FIDE Article 5.2.3: Find the most recent round where p1 and p2 had different colors.
    Returns the round index (0-based) or None if never had alternating colors.
    """
    if not hasattr(p1, "color_history") or not hasattr(p2, "color_history"):
        return None

    p1_colors = _played_colors(p1)
    p2_colors = _played_colors(p2)

    min_len = min(len(p1_colors), len(p2_colors))

    # Look backwards from most recent round to find alternating colors
    for offset in range(1, min_len + 1):
        if p1_colors[-offset] != p2_colors[-offset]:
            return len(p1_colors) - offset

    return None


def _played_colors(player):
    """Compress played colours, ignoring byes and forfeits."""
    outcomes = getattr(player, "outcome_types", [])
    return [
        color
        for i, color in enumerate(player.color_history)
        if color is not None and (i >= len(outcomes) or outcomes[i] == "normal")
    ]


def _get_color_preference(player: Player) -> Optional[str]:
    """
    FIDE Article 1.6.2: Determine player's color preference based on FIDE rules.

    Returns the color preference according to FIDE definitions:
    - Absolute: color difference > +1 or < -1, OR same color in last two rounds
    - Strong: color difference is +1 (prefer black) or -1 (prefer white)
    - Mild: color difference is 0, prefer to alternate from last game
    - None: no games played yet
    """
    if not hasattr(player, "color_history") or not player.color_history:
        return None

    # Filter out None values (byes)
    valid_colors = _played_colors(player)

    if not valid_colors:
        return None

    white_count = valid_colors.count(Colour.WHITE)
    black_count = valid_colors.count(Colour.BLACK)
    color_diff = white_count - black_count

    # FIDE 1.6.2.1: Absolute color preference
    if abs(color_diff) > 1:
        return Colour.BLACK if color_diff > 1 else Colour.WHITE

    # FIDE 1.6.2.1: Absolute - same color in last two rounds
    if len(valid_colors) >= 2 and valid_colors[-1] == valid_colors[-2]:
        return Colour.BLACK if valid_colors[-1] == Colour.WHITE else WHITE

    # FIDE 1.6.2.2: Strong color preference
    if color_diff == 1:
        return Colour.BLACK
    elif color_diff == -1:
        return Colour.WHITE

    # FIDE 1.6.2.3: Mild color preference (color_diff == 0)
    if color_diff == 0 and len(valid_colors) > 0:
        # Prefer to alternate from last game
        return Colour.BLACK if valid_colors[-1] == Colour.WHITE else WHITE

    return None


def _has_absolute_color_preference(player: Player) -> bool:
    """
    FIDE Article 1.6.2.1: Check if player has absolute color preference.
    Absolute occurs when:
    1. Color difference > +1 or < -1, OR
    2. Same color in the two latest rounds played
    """
    if not hasattr(player, "color_history") or not player.color_history:
        return False

    valid_colors = _played_colors(player)

    if len(valid_colors) < 1:
        return False

    white_count = valid_colors.count(Colour.WHITE)
    black_count = valid_colors.count(Colour.BLACK)
    color_diff = white_count - black_count

    # Rule 1: Color difference > +1 or < -1
    if abs(color_diff) > 1:
        return True

    # Rule 2: Same color in last two rounds
    if len(valid_colors) >= 2 and valid_colors[-1] == valid_colors[-2]:
        return True

    return False


def _get_color_imbalance(player: Player) -> int:
    """Get the color imbalance (positive = more whites, negative = more blacks)"""
    if not hasattr(player, "color_history") or not player.color_history:
        return 0

    valid_colors = _played_colors(player)
    white_count = valid_colors.count(Colour.WHITE)
    black_count = valid_colors.count(Colour.BLACK)
    return white_count - black_count


def _get_float_type(player: Player, rounds_back: int, current_round: int) -> FloatType:
    """Determine the float direction of a player in a previous round"""
    if rounds_back >= current_round or rounds_back < 1:
        return FloatType.FLOAT_NONE

    target_round = current_round - rounds_back
    outcome_index = target_round - 1
    if (
        outcome_index < len(player.outcome_types)
        and player.outcome_types[outcome_index] != "normal"
    ):
        score = (
            player.results[outcome_index]
            if outcome_index < len(player.results)
            else None
        )
        return FloatType.FLOAT_DOWN if score and score > 0 else FloatType.FLOAT_NONE
    if target_round <= 0 or target_round > len(player.match_history):
        return FloatType.FLOAT_NONE

    # Get match info for the target round (0-indexed)
    match_index = target_round - 1
    if match_index >= len(player.match_history):
        return FloatType.FLOAT_NONE

    match_info = player.match_history[match_index]
    if not match_info or not match_info.get("opponent_id"):
        # This was a bye round - check if player got points for bye
        if (
            match_index < len(player.results)
            and player.results[match_index]
            and (player.results[match_index] or 0.0) > 0
        ):
            return FloatType.FLOAT_DOWN  # Bye is considered floating down
        return FloatType.FLOAT_NONE

    # Compare player's score with opponent's score from that round
    player_score = match_info.get("player_score", 0.0)
    opponent_score = match_info.get("opponent_score", 0.0)

    if player_score > opponent_score:
        return FloatType.FLOAT_DOWN  # Player had higher score, so floated down
    elif player_score < opponent_score:
        return FloatType.FLOAT_UP  # Player had lower score, so floated up
    else:
        return FloatType.FLOAT_NONE  # Same scores, no float


def _has_strong_color_preference(player: Player) -> bool:
    """
    FIDE Article 1.6.2.2: Check if player has strong (non-absolute) color preference.
    Strong occurs when color difference is +1 or -1.
    """
    if _has_absolute_color_preference(player):
        return False  # Absolute takes precedence

    if not hasattr(player, "color_history") or not player.color_history:
        return False

    valid_colors = _played_colors(player)
    if len(valid_colors) < 1:
        return False

    white_count = valid_colors.count(Colour.WHITE)
    black_count = valid_colors.count(Colour.BLACK)
    return abs(white_count - black_count) == 1
