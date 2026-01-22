"""Core data models for tournament management.

This module defines the fundamental data structures used throughout the tournament system.
"""

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
class TournamentConfig:
    """Configuration settings for a tournament.

    Attributes:
        name: Tournament name
        num_rounds: Number of rounds in the tournament
        pairing_system: Pairing system to use ('dutch_swiss', 'round_robin', 'manual')
        tiebreak_order: List of tiebreak criteria in priority order
    """

    name: str
    num_rounds: int
    pairing_system: str = "dutch_swiss"
    tiebreak_order: List[str] = field(
        default_factory=lambda: list(DEFAULT_TIEBREAK_SORT_ORDER)
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration to dictionary."""
        return {
            "name": self.name,
            "num_rounds": self.num_rounds,
            "pairing_system": self.pairing_system,
            "tiebreak_order": self.tiebreak_order,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TournamentConfig":
        """Deserialize configuration from dictionary."""
        return cls(
            name=data.get("name", "Untitled Tournament"),
            num_rounds=data["num_rounds"],
            pairing_system=data.get("pairing_system", "dutch_swiss"),
            tiebreak_order=data.get(
                "tiebreak_order", list(DEFAULT_TIEBREAK_SORT_ORDER)
            ),
        )


@dataclass
class MatchResult:
    """Represents the result of a single match.

    Attributes:
        white_id: ID of the white player
        black_id: ID of the black player
        white_score: Score for white (1.0 = win, 0.5 = draw, 0.0 = loss)
        black_score: Score for black (computed as 1.0 - white_score)
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


@dataclass
class RoundData:
    """Contains all data for a single round.

    Attributes:
        round_number: The round number (1-indexed)
        pairings: List of tuples (white_player_id, black_player_id)
        bye_player_id: ID of player receiving bye, or None
        results: List of match results (empty until results are recorded)
        is_completed: Whether this round's results have been recorded
    """

    round_number: int
    pairings: List[Tuple[str, str]] = field(default_factory=list)
    bye_player_id: Optional[str] = None
    results: List[MatchResult] = field(default_factory=list)
    is_completed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize round data to dictionary."""
        return {
            "round_number": self.round_number,
            "pairings": self.pairings,
            "bye_player_id": self.bye_player_id,
            "results": [r.to_dict() for r in self.results],
            "is_completed": self.is_completed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoundData":
        """Deserialize round data from dictionary."""
        return cls(
            round_number=data["round_number"],
            pairings=[tuple(p) for p in data.get("pairings", [])],
            bye_player_id=data.get("bye_player_id"),
            results=[MatchResult.from_dict(r) for r in data.get("results", [])],
            is_completed=data.get("is_completed", False),
        )


@dataclass
class PairingHistory:
    """Tracks historical pairings to prevent repeats.

    Attributes:
        previous_matches: Set of frozensets containing player ID pairs who have played
        manual_adjustments: Dict mapping round numbers to manual pairing adjustments
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
