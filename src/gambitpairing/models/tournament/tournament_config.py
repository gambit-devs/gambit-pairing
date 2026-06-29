"""TournamentConfig data class, contains tournament "settings"."""

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
from typing import Any, Dict, List

from gambitpairing.constants import DEFAULT_TIEBREAK_SORT_ORDER


@dataclass(frozen=False)
class TournamentConfig:
    """Tournament configuration settings.

    Attributes
    ----------
    name : str
        Tournament name.
    num_rounds : int
        Number of rounds in the tournament.
    pairing_system : str
        Pairing system used for generating pairings.
    tiebreak_order : list of str
        Ordered list of tiebreak criteria in priority order.
    tournament_over : bool
        Indicates whether the tournament is complete.
    """

    name: str
    num_rounds: int
    pairing_system: str = "dutch_swiss"
    tournament_mode: str = "standard"
    fide_strict_mode: bool = False
    tiebreak_order: List[str] = field(
        default_factory=lambda: list(DEFAULT_TIEBREAK_SORT_ORDER)
    )
    # Is the tournament complete?
    tournament_over: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration to dictionary."""
        return {
            "name": self.name,
            "num_rounds": self.num_rounds,
            "pairing_system": self.pairing_system,
            "tournament_mode": self.tournament_mode,
            "fide_strict_mode": self.fide_strict_mode,
            "tiebreak_order": list(self.tiebreak_order),
            "tournament_over": self.tournament_over,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TournamentConfig":
        """Deserialize configuration from dictionary."""
        return cls(
            name=data.get("name", "Untitled Tournament"),
            num_rounds=data["num_rounds"],
            pairing_system=data.get("pairing_system", "dutch_swiss"),
            tournament_mode=data.get("tournament_mode", "standard"),
            fide_strict_mode=data.get("fide_strict_mode", False),
            tiebreak_order=list(
                data.get("tiebreak_order", DEFAULT_TIEBREAK_SORT_ORDER)
            ),
            tournament_over=data.get("tournament_over", False),
        )


#  LocalWords:  TournamentConfig PairingSystemABC
