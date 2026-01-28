"""Metrics and scoring system for pairing engine comparison.

This module defines the scoring methodology for comparing pairing engines
based on FIDE compliance (70%) and quality metrics (30%).
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

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from gambitpairing.player import Player
from gambitpairing.utils import setup_logger
from gambitpairing.validation.fpc import (
    CriterionStatus,
    ValidationReport,
    ViolationType,
)

logger = setup_logger(__name__)

# FIDE Compliance Violation Penalties (out of 100 points)
VIOLATION_PENALTIES = {
    # Absolute Criteria (C1-C3) - Critical violations
    "C1": -50,  # Repeat pairings
    "C2": -100,  # Self pairings (should never happen)
    "C3": -40,  # Unpaired players (excluding legitimate bye)
    # Quality Criteria (C4-C21) - Progressive penalties
    "C4": -15,  # Color preferences
    "C5": -10,  # Score differences (PSD)
    "C6": -5,  # Color alternation
    "C7": -8,  # Floaters from higher brackets
    "C8": -7,  # Minimize downfloaters
    "C9": -6,  # Color balance
    "C10": -5,  # Rating differences
    "C11": -4,  # Avoid same club/federation
    "C12": -3,  # Title matching
    "C13": -12,  # Bye eligibility (if violated, very bad)
    "C14": -8,  # Multiple byes
    "C15": -6,  # Color preference strength
    "C16": -5,  # Downfloater handling
    "C17": -4,  # MDP management
    "C18": -3,  # Bracket homogeneity
    "C19": -2,  # Local preferences
    "C20": -2,  # Rating accuracy
    "C21": -1,  # Administrative preferences
}

# Quality Metrics Weights (sum to 1.0 for 30% total)
QUALITY_WEIGHTS = {
    "psd_optimization": 0.35,  # Pairing Score Difference
    "color_balance": 0.25,  # Color assignment quality
    "bracket_compliance": 0.20,  # Score bracket adherence
    "float_optimization": 0.10,  # Player movement efficiency
    "tiebreak_consistency": 0.05,  # Standings alignment
    "computational_efficiency": 0.05,  # Performance measurement
}

# Overall scoring weights
FIDE_WEIGHT = 0.7
QUALITY_WEIGHT = 0.3


@dataclass
class QualityMetrics:
    """Quality indicators for pairing evaluation."""

    psd_optimization: float = 0.0  # Lower is better
    color_balance_score: float = 0.0  # 0-100, higher is better
    bracket_compliance: float = 0.0  # 0-100, higher is better
    float_optimization: float = 0.0  # 0-100, higher is better
    tiebreak_consistency: float = 0.0  # 0-100, higher is better
    computational_efficiency: float = 0.0  # 0-100, higher is better

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for serialization."""
        return {
            "psd_optimization": self.psd_optimization,
            "color_balance_score": self.color_balance_score,
            "bracket_compliance": self.bracket_compliance,
            "float_optimization": self.float_optimization,
            "tiebreak_consistency": self.tiebreak_consistency,
            "computational_efficiency": self.computational_efficiency,
        }


@dataclass
class ComparisonMetrics:
    """Complete metrics for a pairing engine evaluation."""

    fide_score: float = 0.0  # 0-100
    quality_score: float = 0.0  # 0-100
    overall_score: float = 0.0  # Weighted combination

    # Detailed breakdowns
    fide_violations: Dict[str, int] = field(default_factory=dict)
    quality_metrics: QualityMetrics = field(default_factory=QualityMetrics)

    # Performance data
    computation_time_ms: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "fide_score": self.fide_score,
            "quality_score": self.quality_score,
            "overall_score": self.overall_score,
            "fide_violations": self.fide_violations,
            "quality_metrics": self.quality_metrics.to_dict(),
            "computation_time_ms": self.computation_time_ms,
        }


def calculate_fide_score(fpc_report: ValidationReport) -> float:
    """Calculate FIDE compliance score from validation report.

    Args:
        fpc_report: Validation report from FPC system

    Returns:
        Score from 0-100, where 100 is perfect compliance
    """
    base_score = 100.0

    for violation in fpc_report.violations:
        if violation.status == CriterionStatus.VIOLATION:
            # Extract criterion number (e.g., "C1" from "C1: No repeat pairings")
            criterion_id = violation.criterion.split(":")[0].strip()

            # Apply penalty if we have one defined
            penalty = VIOLATION_PENALTIES.get(criterion_id, -1)

            # For absolute criteria, penalties are severe
            if violation.violation_type == ViolationType.ABSOLUTE:
                # Count actual violations if available in details
                # Default to 1 if not available
                try:
                    violation_count = (
                        int(violation.details.get("violation_count", 1))
                        if violation.details
                        else 1
                    )
                except (ValueError, TypeError):
                    violation_count = 1
                base_score += penalty * violation_count
            else:
                # Quality criteria: scale by severity
                try:
                    violation_count = (
                        int(violation.details.get("violation_count", 1))
                        if violation.details
                        else 1
                    )
                except (ValueError, TypeError):
                    violation_count = 1
                # Cap quality violations to avoid excessive penalties
                capped_count = min(violation_count, 10)
                base_score += penalty * (capped_count / 10)

    # Ensure score is in valid range
    return max(0.0, min(100.0, base_score))


def calculate_quality_score(
    quality_metrics: QualityMetrics, weights: Optional[Dict[str, float]] = None
) -> float:
    """Calculate overall quality score from individual metrics.

    Args:
        quality_metrics: Quality metrics to evaluate
        weights: Optional custom weights (defaults to QUALITY_WEIGHTS)

    Returns:
        Weighted quality score from 0-100
    """
    if weights is None:
        weights = QUALITY_WEIGHTS

    metrics_dict = quality_metrics.to_dict()

    # Normalize PSD (lower is better, so invert)
    # Assume good PSD is < 2.0, excellent is < 1.0
    psd_normalized = max(0, 100 - (quality_metrics.psd_optimization * 50))

    # Calculate weighted score
    score = (
        psd_normalized * weights["psd_optimization"]
        + metrics_dict["color_balance_score"] * weights["color_balance"]
        + metrics_dict["bracket_compliance"] * weights["bracket_compliance"]
        + metrics_dict["float_optimization"] * weights["float_optimization"]
        + metrics_dict["tiebreak_consistency"] * weights["tiebreak_consistency"]
        + metrics_dict["computational_efficiency"] * weights["computational_efficiency"]
    )

    return max(0.0, min(100.0, score))


def calculate_overall_score(
    fide_score: float,
    quality_score: float,
    fide_weight: float = FIDE_WEIGHT,
    quality_weight: float = QUALITY_WEIGHT,
) -> float:
    """Calculate overall performance score.

    Args:
        fide_score: FIDE compliance score (0-100)
        quality_score: Quality metrics score (0-100)
        fide_weight: Weight for FIDE compliance (default 0.7)
        quality_weight: Weight for quality (default 0.3)

    Returns:
        Overall weighted score (0-100)
    """
    # Normalize weights to ensure they sum to 1.0
    total_weight = fide_weight + quality_weight
    if total_weight > 0:
        fide_weight = fide_weight / total_weight
        quality_weight = quality_weight / total_weight

    overall = (fide_score * fide_weight) + (quality_score * quality_weight)

    return max(0.0, min(100.0, overall))


def calculate_psd(pairings: List[tuple], players_by_id: Dict[str, Player]) -> float:
    """Calculate average Pairing Score Difference (PSD).

    Args:
        pairings: List of (white_player, black_player) tuples
        players_by_id: Dictionary mapping player IDs to Player objects

    Returns:
        Average PSD across all pairings
    """
    if not pairings:
        return 0.0

    total_psd = 0.0
    count = 0

    for white, black in pairings:
        # Get player objects
        white_player = white if isinstance(white, Player) else players_by_id.get(white)
        black_player = black if isinstance(black, Player) else players_by_id.get(black)

        if white_player and black_player:
            score_diff = abs(white_player.score - black_player.score)
            total_psd += score_diff
            count += 1

    return total_psd / count if count > 0 else 0.0


def calculate_color_balance_metric(
    pairings: List[tuple], players_by_id: Dict[str, Player]
) -> float:
    """Calculate color balance quality metric.

    Evaluates how well colors are assigned based on:
    - Color preference adherence
    - Color balance across tournament
    - Due color assignments

    Args:
        pairings: List of (white_player, black_player) tuples
        players_by_id: Dictionary mapping player IDs to Player objects

    Returns:
        Score from 0-100, where 100 is perfect color balance
    """
    if not pairings:
        return 100.0

    total_score = 0.0
    count = 0

    for white, black in pairings:
        white_player = white if isinstance(white, Player) else players_by_id.get(white)
        black_player = black if isinstance(black, Player) else players_by_id.get(black)

        if not white_player or not black_player:
            continue

        pair_score = 100.0

        # Check white player's color preference
        white_pref = white_player.get_color_preference()
        if white_pref == "White":
            pair_score += 0  # Perfect
        elif white_pref == "Black":
            pair_score -= 25  # Bad
        else:
            pair_score -= 10  # Neutral

        # Check black player's color preference
        black_pref = black_player.get_color_preference()
        if black_pref == "Black":
            pair_score += 0  # Perfect
        elif black_pref == "White":
            pair_score -= 25  # Bad
        else:
            pair_score -= 10  # Neutral

        total_score += max(0, pair_score)
        count += 1

    return total_score / count if count > 0 else 100.0


def calculate_bracket_compliance_metric(
    pairings: List[tuple], players_by_id: Dict[str, Player]
) -> float:
    """Calculate score bracket compliance metric.

    Evaluates how well pairings respect score brackets.

    Args:
        pairings: List of (white_player, black_player) tuples
        players_by_id: Dictionary mapping player IDs to Player objects

    Returns:
        Score from 0-100, where 100 is perfect bracket compliance
    """
    if not pairings:
        return 100.0

    same_bracket = 0
    total = 0

    for white, black in pairings:
        white_player = white if isinstance(white, Player) else players_by_id.get(white)
        black_player = black if isinstance(black, Player) else players_by_id.get(black)

        if white_player and black_player:
            if white_player.score == black_player.score:
                same_bracket += 1
            total += 1

    if total == 0:
        return 100.0

    # Score based on percentage of same-bracket pairings
    percentage = (same_bracket / total) * 100

    # Ideal is around 70-80% same bracket (some floats are expected)
    if percentage >= 70:
        return 100.0
    else:
        return percentage * (100 / 70)


def extract_violations_dict(fpc_report: ValidationReport) -> Dict[str, int]:
    """Extract violation counts from FPC report.

    Args:
        fpc_report: Validation report

    Returns:
        Dictionary mapping criterion IDs to violation counts
    """
    violations = {}

    for violation in fpc_report.violations:
        if violation.status == CriterionStatus.VIOLATION:
            criterion_id = violation.criterion.split(":")[0].strip()
            try:
                violations[criterion_id] = (
                    int(violation.details.get("violation_count", 1))
                    if violation.details
                    else 1
                )
            except (ValueError, TypeError):
                violations[criterion_id] = 1

    return violations
