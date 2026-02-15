"""Enums for use in GP, subclass as string for easy serialization."""

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

from enum import Enum


class Colour(str, Enum):
    """A chess colour."""

    WHITE = "White"
    BLACK = "Black"


class TournamentPhase(str, Enum):
    """
    Represents the current phase of a tournament.

    Used to determine which UI elements and actions should be available.
    """

    NO_TOURNAMENT = "NT"  # No tournament loaded
    NOT_STARTED = "NS"  # Tournament exists but hasn't started
    AWAITING_RESULTS = "AR"  # Pairings generated, waiting for results
    AWAITING_NEXT_ROUND = "AN"  # Results recorded, ready for next round
    FINISHED = "DN"  # All rounds completed
