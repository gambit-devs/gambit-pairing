"""Data model for tournament round."""

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

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from gambitpairing.constants import DEFAULT_TIEBREAK_SORT_ORDER


@dataclass
class RoundData:
    """Container for all data related to a single tournament round.

    Attributes
    ----------
    round_number : int
        Round number.
    pairings : list of tuple of str
        List of (white_player_id, black_player_id) pairs.
    bye_player_id : str or None
        ID of the player receiving a bye, or None if no bye was assigned.
    results : list
        List of recorded match results. Empty until results are recorded.
    is_completed : bool
        Indicates whether the round's results have been finalized.
    """

    round_number: int
    pairings: List[Tuple[str, str]] = field(default_factory=list)
    bye_player_id: Optional[str] = None
    results: List[MatchResult] = field(default_factory=list)
    is_completed: bool = False
