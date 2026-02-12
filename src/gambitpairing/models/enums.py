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


class PairingSystem(str, Enum):
    DUTCH_SWISS = "dutch_swiss"
    ROUND_ROBIN = "round_robin"
    MANUAL = "manual"


class Colour(str, Enum):
    WHITE = "White"
    BLACK = "Black"
