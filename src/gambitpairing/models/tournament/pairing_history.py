"""Data models for tournament round."""

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


@dataclass
class PairingHistory:
    """
    Tracks historical pairings to prevent repeat matches.

    Attributes
    ----------
    previous_matches : set of frozenset of str
        Set containing frozensets of player ID pairs representing
        matches that have already been played.
    manual_adjustments : dict of int to Any
        Mapping of round numbers to manual pairing adjustments.
    """

    previous_matches: Set[frozenset] = field(default_factory=set)
    manual_adjustments: Dict[int, Dict[str, str]] = field(default_factory=dict)

    def add_pairing(self, player1_id: str, player2_id: str) -> None:
        """Record that two players have been paired."""
        self.previous_matches.add(frozenset({player1_id, player2_id}))

    def have_played(self, player1_id: str, player2_id: str) -> bool:
        """Check if two players have previously played each other."""
        return frozenset({player1_id, player2_id}) in self.previous_matches

    def to_dict(self) -> Dict[str, Any]:
        """Serialize pairing history to dictionary."""
        return {
            "previous_matches": [list(pair) for pair in self.previous_matches],
            "manual_adjustments": self.manual_adjustments,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PairingHistory":
        """Deserialize pairing history from dictionary."""
        return cls(
            previous_matches=set(
                frozenset(map(str, pair)) for pair in data.get("previous_matches", [])
            ),
            manual_adjustments={
                int(k): v for k, v in data.get("manual_adjustments", {}).items()
            },
        )
