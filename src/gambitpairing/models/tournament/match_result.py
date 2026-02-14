"""Match result data class."""

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

from dataclasses import dataclass


@dataclass
class MatchResult:
    """Represents the result of a single match.

    Attributes
    ----------
    white_id: str
        ID of the white player
    black_id : str
        ID of the black player
    white_score : float
        Score for white (1.0 = win, 0.5 = draw, 0.0 = loss)
    black_score : float
        Score for black (computed as 1.0 - white_score)
    """

    white_id: str
    black_id: str
    white_score: float

    @property
    def black_score(self) -> float:
        """Calculate black's score based on white's score."""
        return 1.0 - self.white_score

    def to_dict(self) -> Dict[str, Any]:
        """Serialize match result to dictionary."""
        return {
            "white_id": self.white_id,
            "black_id": self.black_id,
            "white_score": self.white_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MatchResult":
        """Deserialize match result from dictionary."""
        return cls(
            white_id=data["white_id"],
            black_id=data["black_id"],
            white_score=data["white_score"],
        )
