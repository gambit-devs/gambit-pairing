"""Tournament management system for Gambit Pairing.

This package provides a professionally designed tournament management system
with clean separation of concerns and well-defined responsibilities.
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

from gambitpairing.tournament.models import MatchResult, RoundData, TournamentConfig
from gambitpairing.tournament.result_recorder import ResultRecorder
from gambitpairing.tournament.round_manager import RoundManager
from gambitpairing.tournament.tiebreak_calculator import TiebreakCalculator
from gambitpairing.tournament.tournament import Tournament

__all__ = [
    "Tournament",
    "TournamentConfig",
    "RoundData",
    "MatchResult",
    "RoundManager",
    "ResultRecorder",
    "TiebreakCalculator",
]
