"""Testing module for Gambit Pairing.

This module provides comprehensive testing functionality including:
- Random Tournament Generator (RTG)
- Pairing engine comparison
- FIDE validation
- Unit testing
- Benchmarking

Use the unified CLI: gambit-test
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

from gambitpairing.testing.rtg import (
    RandomTournamentGenerator,
    RatingDistribution,
    ResultPattern,
    RTGConfig,
)

__all__ = [
    "RandomTournamentGenerator",
    "RTGConfig",
    "RatingDistribution",
    "ResultPattern",
]
