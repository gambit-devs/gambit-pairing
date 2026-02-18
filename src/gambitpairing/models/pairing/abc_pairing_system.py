"""A chess tournament pairing system."""

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


from abc import ABC, abstractmethod
from typing import List, Set

from gambitpairing.models.player import PlayerABC


class PairingSystemABC(ABC):
    """Abstract interface for tournament pairing systems."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the pairing system."""
        raise NotImplementedError

    @abstractmethod
    def pair_round(
        self,
        players: List[PlayerABC],
        *,
        current_round: int,
        previous_matches: Set[frozenset[str]],
        total_rounds: int | None = None,
    ):
        """Generate pairings for a round."""
        raise NotImplementedError
