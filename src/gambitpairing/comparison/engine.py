"""Core comparison engine for evaluating pairing engines.

This module provides the main comparison logic for evaluating Gambit vs BBP
pairing engines across multiple tournaments and rounds.
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

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from gambitpairing.comparison.metrics import (
    ComparisonMetrics,
    QualityMetrics,
    calculate_bracket_compliance_metric,
    calculate_color_balance_metric,
    calculate_fide_score,
    calculate_overall_score,
    calculate_psd,
    calculate_quality_score,
    extract_violations_dict,
)
from gambitpairing.comparison.validator import create_comparison_validator
from gambitpairing.player import Player
from gambitpairing.utils import setup_logger
from gambitpairing.validation.fpc import ValidationReport

logger = setup_logger(__name__)


@dataclass
class PairingDifference:
    """Represents a difference between two pairing sets."""

    matching_pairs: int = 0
    gambit_only_pairs: List[Tuple[str, str]] = field(default_factory=list)
    bbp_only_pairs: List[Tuple[str, str]] = field(default_factory=list)
    different_colors: List[Tuple[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "matching_pairs": self.matching_pairs,
            "matching_percentage": self.matching_percentage,
            "gambit_only_pairs": self.gambit_only_pairs,
            "bbp_only_pairs": self.bbp_only_pairs,
            "different_colors": self.different_colors,
            "total_differences": len(self.gambit_only_pairs) + len(self.bbp_only_pairs),
        }

    @property
    def matching_percentage(self) -> float:
        """Calculate percentage of matching pairs."""
        total_pairs = (
            self.matching_pairs + len(self.gambit_only_pairs) + len(self.bbp_only_pairs)
        )
        if total_pairs == 0:
            return 100.0
        return (self.matching_pairs / total_pairs) * 100


@dataclass
class ComparisonResult:
    """Complete comparison result for a single tournament or round."""

    tournament_id: str
    round_number: Optional[int] = None

    # Pairing data
    gambit_pairings: List[Tuple[Player, Player]] = field(default_factory=list)
    bbp_pairings: List[Tuple[Player, Player]] = field(default_factory=list)
    gambit_bye: Optional[Player] = None
    bbp_bye: Optional[Player] = None

    # Validation reports
    fpc_gambit: Optional[ValidationReport] = None
    fpc_bbp: Optional[ValidationReport] = None

    # Computed metrics
    gambit_metrics: Optional[ComparisonMetrics] = None
    bbp_metrics: Optional[ComparisonMetrics] = None

    # Pairing differences
    pairing_differences: Optional[PairingDifference] = None

    # Winner determination
    winner: Optional[str] = None  # "gambit", "bbp", or "tie"
    score_difference: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        result = {
            "tournament_id": self.tournament_id,
            "round_number": self.round_number,
            "winner": self.winner,
            "score_difference": self.score_difference,
        }

        if self.gambit_metrics:
            result["gambit_metrics"] = self.gambit_metrics.to_dict()

        if self.bbp_metrics:
            result["bbp_metrics"] = self.bbp_metrics.to_dict()

        if self.pairing_differences:
            result["pairing_differences"] = self.pairing_differences.to_dict()

        if self.fpc_gambit:
            result["gambit_compliance"] = {
                "percentage": self.fpc_gambit.compliance_percentage,
                "summary": self.fpc_gambit.summary,
            }

        if self.fpc_bbp:
            result["bbp_compliance"] = {
                "percentage": self.fpc_bbp.compliance_percentage,
                "summary": self.fpc_bbp.summary,
            }

        return result


class PairingComparisonEngine:
    """Main engine for comparing pairing systems."""

    def __init__(
        self,
        fide_weight: float = 0.7,
        quality_weight: float = 0.3,
    ):
        """Initialize the comparison engine.

        Args:
            fide_weight: Weight for FIDE compliance (default 0.7)
            quality_weight: Weight for quality metrics (default 0.3)
        """
        self.fide_weight = fide_weight
        self.quality_weight = quality_weight
        self.validator = create_comparison_validator()
        logger.info(
            "Initialized comparison engine (FIDE: %.1f%%, Quality: %.1f%%)",
            fide_weight * 100,
            quality_weight * 100,
        )

    def compare_pairings(
        self,
        tournament_id: str,
        gambit_pairings: List[Tuple[Player, Player]],
        bbp_pairings: List[Tuple[Player, Player]],
        gambit_bye: Optional[Player] = None,
        bbp_bye: Optional[Player] = None,
        players: Optional[List[Player]] = None,
        round_number: int = 1,
        total_rounds: int = 1,
        gambit_time_ms: float = 0.0,
        bbp_time_ms: float = 0.0,
        previous_matches: Optional[set] = None,
        player_bye_history: Optional[Dict[str, int]] = None,
    ) -> ComparisonResult:
        """Compare two pairing sets from different engines.

        Args:
            tournament_id: Unique identifier for tournament
            gambit_pairings: Pairings from Gambit engine
            bbp_pairings: Pairings from BBP engine
            gambit_bye: Player receiving bye in Gambit
            bbp_bye: Player receiving bye in BBP
            players: All players (for validation)
            round_number: Current round number
            total_rounds: Total rounds in tournament
            gambit_time_ms: Time taken for Gambit pairing (milliseconds)
            bbp_time_ms: Time taken for BBP pairing (milliseconds)

        Returns:
            Comprehensive comparison result
        """
        result = ComparisonResult(
            tournament_id=tournament_id,
            round_number=round_number,
            gambit_pairings=gambit_pairings,
            bbp_pairings=bbp_pairings,
            gambit_bye=gambit_bye,
            bbp_bye=bbp_bye,
        )

        # Analyze pairing differences
        result.pairing_differences = self._analyze_pairing_differences(
            gambit_pairings, bbp_pairings
        )

        # Validate both pairing sets if players provided
        if players:
            result.fpc_gambit = self.validator.validate_pairings_for_comparison(
                gambit_pairings,
                gambit_bye,
                players,
                round_number,
                total_rounds,
                previous_matches=previous_matches,
                player_bye_history=player_bye_history,
            )
            result.fpc_bbp = self.validator.validate_pairings_for_comparison(
                bbp_pairings,
                bbp_bye,
                players,
                round_number,
                total_rounds,
                previous_matches=previous_matches,
                player_bye_history=player_bye_history,
            )

        # Calculate metrics for both engines
        result.gambit_metrics = self._calculate_metrics(
            gambit_pairings,
            result.fpc_gambit,
            players,
            gambit_time_ms,
        )

        result.bbp_metrics = self._calculate_metrics(
            bbp_pairings,
            result.fpc_bbp,
            players,
            bbp_time_ms,
        )

        # Determine winner
        result.winner, result.score_difference = self._determine_winner(
            result.gambit_metrics,
            result.bbp_metrics,
        )

        logger.info(
            "Comparison complete: %s wins by %.2f points (Round %d)",
            result.winner,
            result.score_difference,
            round_number,
        )

        return result

    def compare_tournaments(
        self,
        tournaments: List[Dict],
    ) -> List[ComparisonResult]:
        """Compare multiple tournaments.

        Args:
            tournaments: List of tournament data with both pairing sets

        Returns:
            List of comparison results
        """
        results = []

        for tournament in tournaments:
            # Extract tournament data
            tournament_id = tournament.get("id", f"tournament_{len(results)}")
            rounds = tournament.get("rounds", [])
            players = tournament.get("players", [])
            total_rounds = len(rounds)

            for round_data in rounds:
                round_num = round_data.get("round_number", 1)

                # Extract Gambit pairings
                gambit_pairings = round_data.get("gambit_pairings", [])
                gambit_bye_id = round_data.get("gambit_bye_player_id")
                gambit_bye = self._find_player(players, gambit_bye_id)
                gambit_time = round_data.get("gambit_time_ms", 0.0)

                # Extract BBP pairings
                bbp_pairings = round_data.get("bbp_pairings", [])
                bbp_bye_id = round_data.get("bbp_bye_player_id")
                bbp_bye = self._find_player(players, bbp_bye_id)
                bbp_time = round_data.get("bbp_time_ms", 0.0)

                # Compare this round
                result = self.compare_pairings(
                    tournament_id=tournament_id,
                    gambit_pairings=gambit_pairings,
                    bbp_pairings=bbp_pairings,
                    gambit_bye=gambit_bye,
                    bbp_bye=bbp_bye,
                    players=players,
                    round_number=round_num,
                    total_rounds=total_rounds,
                    gambit_time_ms=gambit_time,
                    bbp_time_ms=bbp_time,
                )

                results.append(result)

        return results

    def _analyze_pairing_differences(
        self,
        gambit_pairings: List[Tuple[Player, Player]],
        bbp_pairings: List[Tuple[Player, Player]],
    ) -> PairingDifference:
        """Analyze differences between two pairing sets.

        Args:
            gambit_pairings: Pairings from Gambit
            bbp_pairings: Pairings from BBP

        Returns:
            Detailed pairing differences
        """
        diff = PairingDifference()

        # Convert to sets of player ID pairs (order-independent)
        def to_set(pairings: List[Tuple[Player, Player]]) -> Set[Tuple[str, str]]:
            return {tuple(sorted([w.id, b.id])) for w, b in pairings}

        gambit_set = to_set(gambit_pairings)
        bbp_set = to_set(bbp_pairings)

        # Find matching and different pairs
        matching = gambit_set & bbp_set
        diff.matching_pairs = len(matching)
        diff.gambit_only_pairs = list(gambit_set - bbp_set)
        diff.bbp_only_pairs = list(bbp_set - gambit_set)

        # Check for color differences in matching pairs
        gambit_colors = {
            tuple(sorted([w.id, b.id])): (w.id, b.id) for w, b in gambit_pairings
        }
        bbp_colors = {
            tuple(sorted([w.id, b.id])): (w.id, b.id) for w, b in bbp_pairings
        }

        for pair in matching:
            if gambit_colors.get(pair) != bbp_colors.get(pair):
                diff.different_colors.append(pair)

        return diff

    def _calculate_metrics(
        self,
        pairings: List[Tuple[Player, Player]],
        fpc_report: Optional[ValidationReport],
        players: Optional[List[Player]],
        computation_time_ms: float,
    ) -> ComparisonMetrics:
        """Calculate comprehensive metrics for a pairing set.

        Args:
            pairings: Pairing set to evaluate
            fpc_report: Validation report
            players: All players
            computation_time_ms: Time taken to generate pairings

        Returns:
            Complete metrics
        """
        metrics = ComparisonMetrics()
        metrics.computation_time_ms = computation_time_ms

        # Calculate FIDE score
        if fpc_report:
            metrics.fide_score = calculate_fide_score(fpc_report)
            metrics.fide_violations = extract_violations_dict(fpc_report)
        else:
            metrics.fide_score = 0.0

        # Calculate quality metrics
        if players and pairings:
            players_by_id = {p.id: p for p in players}

            quality = QualityMetrics()
            quality.psd_optimization = calculate_psd(pairings, players_by_id)
            quality.color_balance_score = calculate_color_balance_metric(
                pairings, players_by_id
            )
            quality.bracket_compliance = calculate_bracket_compliance_metric(
                pairings, players_by_id
            )

            # Float optimization (simplified - higher is better)
            quality.float_optimization = 80.0  # Placeholder

            # Tiebreak consistency (simplified)
            quality.tiebreak_consistency = 85.0  # Placeholder

            # Computational efficiency (faster is better)
            # Normalize to 0-100 where <100ms = 100, >5000ms = 0
            if computation_time_ms > 0:
                eff = max(0, 100 - (computation_time_ms / 50))
                quality.computational_efficiency = min(100, eff)
            else:
                quality.computational_efficiency = 100.0

            metrics.quality_metrics = quality
            metrics.quality_score = calculate_quality_score(quality)

        # Calculate overall score
        metrics.overall_score = calculate_overall_score(
            metrics.fide_score,
            metrics.quality_score,
            self.fide_weight,
            self.quality_weight,
        )

        return metrics

    def _determine_winner(
        self,
        gambit_metrics: ComparisonMetrics,
        bbp_metrics: ComparisonMetrics,
    ) -> Tuple[str, float]:
        """Determine which engine performed better.

        Args:
            gambit_metrics: Metrics for Gambit
            bbp_metrics: Metrics for BBP

        Returns:
            Tuple of (winner_name, score_difference)
        """
        diff = gambit_metrics.overall_score - bbp_metrics.overall_score

        # Tie threshold: within 1% is considered a tie
        if abs(diff) < 1.0:
            return "tie", 0.0
        elif diff > 0:
            return "gambit", diff
        else:
            return "bbp", abs(diff)

    def _find_player(
        self,
        players: List[Player],
        player_id: Optional[str],
    ) -> Optional[Player]:
        """Find a player by ID.

        Args:
            players: List of players
            player_id: Player ID to find

        Returns:
            Player object or None
        """
        if not player_id:
            return None

        for player in players:
            if player.id == player_id:
                return player

        return None
