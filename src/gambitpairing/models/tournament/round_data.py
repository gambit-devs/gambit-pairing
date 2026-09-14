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
from typing import Any, Dict, List, Optional, Tuple

from .match_result import MatchResult


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
    pending_results : list
        Results entered in the workspace but not yet applied to player scores.
    """

    round_number: int
    pairings: List[Tuple[str, str]] = field(default_factory=list)
    bye_player_id: Optional[str] = None
    results: List[MatchResult] = field(default_factory=list)
    is_completed: bool = False
    # Results entered in the Rounds workspace but not yet finalized.  Keeping
    # these separate from ``results`` means the UI can autosave data-entry
    # progress without changing standings or player histories prematurely.
    pending_results: List[MatchResult] = field(default_factory=list)
    bye_type: str = "full"
    active_player_ids: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.bye_type not in {"full", "half", "zero"}:
            raise ValueError("Bye type must be full, half, or zero")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize round data to dictionary."""
        data = {
            "round_number": self.round_number,
            "pairings": self.pairings,
            "bye_player_id": self.bye_player_id,
            "bye_type": self.bye_type,
            "results": [result.to_dict() for result in self.results],
            "is_completed": self.is_completed,
        }
        if self.pending_results:
            data["pending_results"] = [
                result.to_dict() for result in self.pending_results
            ]
        if self.active_player_ids is not None:
            data["active_player_ids"] = list(self.active_player_ids)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoundData":
        """Deserialize round data from dictionary."""
        return cls(
            round_number=data["round_number"],
            pairings=[tuple(pair) for pair in data.get("pairings", [])],
            bye_player_id=data.get("bye_player_id"),
            bye_type=data.get("bye_type", "full"),
            active_player_ids=data.get("active_player_ids"),
            results=[
                MatchResult.from_dict(result) for result in data.get("results", [])
            ],
            is_completed=data.get("is_completed", False),
            pending_results=[
                MatchResult.from_dict(result)
                for result in data.get("pending_results", [])
            ],
        )
