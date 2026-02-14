"""PairingResult data class."""

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


from typing import List, Optional, Tuple
from dataclasses import dataclass
from __future__ import annotation

from gambitpairing.models.player import Player
from gambitpairing.type_hints import Pairing, PairingIDs


@dataclass(slots=True)
class PairingResult:
    """Result of a pairing computation for a single round."""

    pairings: List[Pairing]
    bye_player: Optional[Player]
    pairing_ids: List[PairingIDs]
    bye_player_id: Optional[str]


#  LocalWords:  PairingResult
