"""Comparison module for evaluating Gambit vs BBP pairing engines.

This module provides comprehensive comparison, analysis, and reporting
capabilities for comparing the Gambit pairing engine against BBP (BieremaBoyz
Programming Pairings) implementation.
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

from gambitpairing.comparison.analyzer import (
    StatisticalAnalyzer,
    StatisticalSummary,
)
from gambitpairing.comparison.engine import (
    ComparisonResult,
    PairingComparisonEngine,
)
from gambitpairing.comparison.metrics import (
    ComparisonMetrics,
    calculate_fide_score,
    calculate_overall_score,
    calculate_quality_score,
)
from gambitpairing.comparison.reporter import (
    ComparisonReporter,
    generate_comprehensive_report,
)

__all__ = [
    "ComparisonMetrics",
    "calculate_overall_score",
    "calculate_fide_score",
    "calculate_quality_score",
    "PairingComparisonEngine",
    "ComparisonResult",
    "StatisticalAnalyzer",
    "StatisticalSummary",
    "ComparisonReporter",
    "generate_comprehensive_report",
]
