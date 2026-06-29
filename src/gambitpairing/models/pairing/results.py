"""Result data class."""

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
from dataclasses import dataclass
from typing import List, Optional, Tuple
from gambitpairing.models.player import Player


@dataclass
class PairingGenerationResult:
    """Result of a pairing generation operation."""

    success: bool
    pairings: List[Tuple[Player, Player]]
    bye_player: Optional[Player]
    error_message: Optional[str] = None


@dataclass
class RecordingResult:
    """Result of a result recording operation."""

    success: bool
    error_message: Optional[str] = None
    tournament_finished: bool = False


@dataclass
class ValidationResult:
    """Result of a validation check."""

    valid: bool
    error_message: Optional[str] = None
    needs_confirmation: bool = False
    confirmation_message: Optional[str] = None
