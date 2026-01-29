"""Enhanced FIDE validation wrapper for comparison analysis.

This module provides specialized validation functionality for the comparison
system, wrapping and extending the core FPC validator.
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

from typing import Dict, List, Optional, Tuple

from gambitpairing.player import Player
from gambitpairing.utils import setup_logger
from gambitpairing.validation.fpc import (
    CriterionStatus,
    ValidationReport,
    create_fpc_validator,
)

logger = setup_logger(__name__)


class ComparisonValidator:
    """Enhanced validator for pairing comparison analysis."""

    def __init__(self):
        """Initialize the comparison validator."""
        self.fpc_validator = create_fpc_validator()

    def validate_pairings_for_comparison(
        self,
        pairings: List[Tuple[Player, Player]],
        bye_player: Optional[Player],
        players: List[Player],
        round_number: int,
        total_rounds: int,
        previous_matches: Optional[set] = None,
        player_bye_history: Optional[Dict[str, int]] = None,
    ) -> ValidationReport:
        """Validate pairings for a single round in comparison mode.

        Args:
            pairings: List of (white_player, black_player) tuples
            bye_player: Player receiving bye, if any
            players: All players in tournament
            round_number: Current round number
            total_rounds: Total rounds in tournament

        Returns:
            Detailed validation report
        """
        # Convert pairings to ID format for validator
        pairing_ids = [(white.id, black.id) for white, black in pairings]
        bye_player_id = bye_player.id if bye_player else None

        # Create round data structure
        round_data = {
            "round_number": round_number,
            "pairings": pairing_ids,
            "bye_player_id": bye_player_id,
            "results": [],  # Results not available during pairing validation
        }

        previous_matches = previous_matches or set()
        player_bye_history = player_bye_history or {}

        # Validate using FPC
        report = self.fpc_validator.validate_round_pairings(
            pairings=pairings,
            bye_player=bye_player,
            current_round=round_number,
            total_rounds=total_rounds,
            previous_matches=previous_matches,
            player_bye_history=player_bye_history,
            players=players,
        )

        return report

    def validate_tournament_for_comparison(
        self,
        tournament_data: Dict,
    ) -> ValidationReport:
        """Validate complete tournament for comparison.

        Args:
            tournament_data: Complete tournament data structure

        Returns:
            Comprehensive tournament validation report
        """
        return self.fpc_validator.validate_tournament_compliance(tournament_data)

    def compare_validation_reports(
        self,
        gambit_report: ValidationReport,
        bbp_report: ValidationReport,
    ) -> Dict[str, any]:
        """Compare two validation reports side-by-side.

        Args:
            gambit_report: Validation report for Gambit pairings
            bbp_report: Validation report for BBP pairings

        Returns:
            Detailed comparison showing differences
        """
        comparison = {
            "gambit_compliance": gambit_report.compliance_percentage,
            "bbp_compliance": bbp_report.compliance_percentage,
            "compliance_difference": (
                gambit_report.compliance_percentage - bbp_report.compliance_percentage
            ),
            "gambit_violations": self._extract_violation_summary(gambit_report),
            "bbp_violations": self._extract_violation_summary(bbp_report),
            "unique_gambit_violations": [],
            "unique_bbp_violations": [],
            "common_violations": [],
        }

        # Identify unique and common violations
        gambit_violation_ids = set(
            v.criterion_id
            for v in gambit_report.violations
            if v.status == CriterionStatus.VIOLATION
        )
        bbp_violation_ids = set(
            v.criterion_id
            for v in bbp_report.violations
            if v.status == CriterionStatus.VIOLATION
        )

        comparison["unique_gambit_violations"] = list(
            gambit_violation_ids - bbp_violation_ids
        )
        comparison["unique_bbp_violations"] = list(
            bbp_violation_ids - gambit_violation_ids
        )
        comparison["common_violations"] = list(gambit_violation_ids & bbp_violation_ids)

        return comparison

    def _extract_violation_summary(self, report: ValidationReport) -> Dict[str, int]:
        """Extract summary of violations by criterion.

        Args:
            report: Validation report

        Returns:
            Dictionary mapping criterion IDs to violation counts
        """
        violations = {}
        for violation in report.violations:
            if violation.status == CriterionStatus.VIOLATION:
                criterion_id = violation.criterion.split(":")[0].strip()
                violations[criterion_id] = violation.violation_count or 1

        return violations


def create_comparison_validator() -> ComparisonValidator:
    """Factory function to create a comparison validator.

    Returns:
        New ComparisonValidator instance
    """
    return ComparisonValidator()
