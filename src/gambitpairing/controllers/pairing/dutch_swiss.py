"""Dutch Swiss Pairing System Implementation."""

# Gambit Pairing
# Copyright (C) 2025  Gambit Pairing developers
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import annotations

from contextvars import ContextVar
from enum import Enum
import math
import time
from typing import Dict, List, Optional, Set, Tuple

from gambitpairing.models.enums import Colour
from gambitpairing.models.player import Player
from gambitpairing.exceptions import PairingTimeoutException
from gambitpairing.utils import setup_logger

WHITE = Colour.WHITE
BLACK = Colour.BLACK
logger = setup_logger(__name__)


class _PairingDeadlineExceeded(Exception):
    """Signal that a pairing search has exhausted its computation budget."""


_pairing_deadline: ContextVar[Optional[float]] = ContextVar(
    "pairing_deadline", default=None
)


def _check_pairing_deadline() -> None:
    deadline = _pairing_deadline.get()
    if deadline is not None and time.monotonic() >= deadline:
        raise _PairingDeadlineExceeded


def _restore_pairing_state(
    players: List[Player],
    pairing_state: Dict[str, Tuple[Optional[int], Optional[int], bool, List[int]]],
) -> None:
    """Restore player fields that pairing search uses as working state."""
    for player in players:
        state = pairing_state.get(player.id)
        if state is None:
            continue
        pairing_number, bsn, is_moved_down, float_history = state
        player.pairing_number = pairing_number
        player.bsn = bsn
        player.is_moved_down = is_moved_down
        player.float_history = list(float_history)


def _pairing_number(player: Player) -> int:
    return player.pairing_number or 0


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


def _sort_players_for_pairing(players: List[Player]) -> List[Player]:
    """Sort players by score descending, then pairing number ascending."""
    return sorted(players, key=lambda p: (-p.score, _pairing_number(p)))


class FloatType(Enum):
    """Types of floaters based on C++ implementation"""

    FLOAT_DOWN = 1
    FLOAT_UP = 2
    FLOAT_NONE = 3


# FIDE Dutch Swiss pairing algorithm implementation
# Based on the C++ reference implementation, adapted for Python
def create_dutch_swiss_pairings(
    players: List[Player],
    current_round: int,
    previous_matches: Set[frozenset],
    get_eligible_bye_player,
    allow_repeat_pairing_callback=None,
    total_rounds: int = 0,
    initial_color: str = WHITE,
    fide_strict: bool = False,
    max_computation_time: Optional[float] = None,
) -> Tuple[
    List[Tuple[Player, Player]], Optional[Player], List[Tuple[str, str]], Optional[str]
]:
    """
    Create pairings for a Swiss-system round using the FIDE Dutch system.
    Optimized for performance with large player pools while maintaining FIDE compliance.

    - players: list of Player objects
    - current_round: The 1-based index of the current round.
    - previous_matches: set of frozenset({player1.id, player2.id}) for all previous matches
    - get_eligible_bye_player: A function to select a player to receive a bye.
    - allow_repeat_pairing_callback: function(player1, player2) -> bool, called if a repeat pairing is needed
    Returns: (pairings, bye_player, round_pairings_ids, bye_player_id)
    """
    # Retain the argument for saved-document/API compatibility, but never
    # weaken legality or return an approximate pairing on deadline expiry.
    fide_strict = True  # Compatibility argument cannot enable approximate pairing.
    player_count = len([p for p in players if p.is_active])
    time_cap = 120.0 if fide_strict else 60.0
    min_time = 20.0 if fide_strict else 15.0
    multiplier = 1.0 if fide_strict else 0.5
    default_time_budget = min(time_cap, max(min_time, player_count * multiplier))
    if max_computation_time is None:
        time_budget = default_time_budget
    else:
        try:
            time_budget = float(max_computation_time)
        except (TypeError, ValueError) as error:
            raise ValueError("max_computation_time must be numeric") from error
        if not math.isfinite(time_budget) or time_budget <= 0:
            raise ValueError("max_computation_time must be finite and positive")

    active_players = [p for p in players if p.is_active]
    pairing_state = {
        player.id: (
            player.pairing_number,
            player.bsn,
            player.is_moved_down,
            list(player.float_history),
        )
        for player in active_players
    }
    deadline_token = _pairing_deadline.set(time.monotonic() + time_budget)
    try:
        _check_pairing_deadline()

        # Preserve established TPNs; allocate missing numbers in strength order.
        used_numbers = {
            p.pairing_number for p in active_players if p.pairing_number is not None
        }
        missing_number = 1
        for p in sorted(active_players, key=lambda p: (-p.rating, p.name, p.id)):
            if not hasattr(p, "pairing_number") or p.pairing_number is None:
                while missing_number in used_numbers:
                    missing_number += 1
                p.pairing_number = missing_number
                used_numbers.add(missing_number)

        sorted_players = _sort_players_for_pairing(active_players)

        from .strict_dutch import pair_round

        return pair_round(
            sorted_players,
            previous_matches,
            current_round,
            total_rounds,
            initial_color,
            _check_pairing_deadline,
        )
    except _PairingDeadlineExceeded:
        _restore_pairing_state(active_players, pairing_state)
        raise PairingTimeoutException(
            f"GP Dutch search timed out in round {current_round}; no pairings committed"
        ) from None
    except Exception:
        _restore_pairing_state(active_players, pairing_state)
        raise
    finally:
        _pairing_deadline.reset(deadline_token)


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
    if _pairing_number(higher_ranked) % 2 == 1:
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


def _has_three_consecutive_colors(player: Player) -> bool:
    """Check if player has same color three times in a row (for C11)"""
    if not hasattr(player, "color_history") or not player.color_history:
        return False

    valid_colors = _played_colors(player)
    if len(valid_colors) < 3:
        return False

    # Check last three games
    return valid_colors[-1] == valid_colors[-2] == valid_colors[-3]


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
