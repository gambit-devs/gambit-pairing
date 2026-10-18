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

from .dutch_rules import (
    WHITE,
    _pairing_number,
    _played_colors,
)

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


def _sort_players_for_pairing(players: List[Player]) -> List[Player]:
    """Sort players by score descending, then pairing number ascending."""
    return sorted(players, key=lambda p: (-p.score, _pairing_number(p)))


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


def _has_three_consecutive_colors(player: Player) -> bool:
    """Check if player has same color three times in a row (for C11)"""
    if not hasattr(player, "color_history") or not player.color_history:
        return False

    valid_colors = _played_colors(player)
    if len(valid_colors) < 3:
        return False

    # Check last three games
    return valid_colors[-1] == valid_colors[-2] == valid_colors[-3]
