"""Main Tournament model master of all tournament data."""

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

from dataclasses import dataclass, field
from typing import List

from gambitpairing.type_aliases import Players

from .pairing_history import PairingHistory
from .round_data import RoundData
from .tournament_config import TournamentConfig


@dataclass
class Tournament:
    """Tournament data, nothing else.

    Holds all domain state for a tournament but performs no STUFF.
    """

    config: TournamentConfig
    players: Players
    rounds: List[RoundData] = field(default_factory=list)
    pairing_history: PairingHistory = field(default_factory=PairingHistory)
