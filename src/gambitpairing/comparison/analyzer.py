"""Statistical analysis engine for multi-tournament comparison.

This module provides statistical analysis capabilities for comparing pairing
engines across many tournaments to determine overall performance and patterns.
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

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from gambitpairing.comparison.engine import ComparisonResult
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


@dataclass
class StatisticalSummary:
    """Statistical summary of multiple tournament comparisons."""

    total_comparisons: int = 0
    gambit_wins: int = 0
    bbp_wins: int = 0
    ties: int = 0

    # Win rates
    gambit_win_rate: float = 0.0
    bbp_win_rate: float = 0.0
    tie_rate: float = 0.0

    # Score statistics
    average_score_difference: float = 0.0
    median_score_difference: float = 0.0
    max_score_difference: float = 0.0
    min_score_difference: float = 0.0
    stddev_score_difference: float = 0.0

    # Statistical significance
    statistical_significance: float = 0.0
    confidence_level: float = 0.0

    # Detailed breakdowns
    fide_comparison: Dict[str, float] = field(default_factory=dict)
    quality_comparison: Dict[str, float] = field(default_factory=dict)

    # Performance by tournament characteristics
    size_based_performance: Dict[str, Dict] = field(default_factory=dict)
    round_based_performance: Dict[int, Dict] = field(default_factory=dict)

    # Violation patterns
    violation_patterns: Dict[str, Dict] = field(default_factory=dict)

    # Computational efficiency
    performance_stats: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "total_comparisons": self.total_comparisons,
            "gambit_wins": self.gambit_wins,
            "bbp_wins": self.bbp_wins,
            "ties": self.ties,
            "gambit_win_rate": self.gambit_win_rate,
            "bbp_win_rate": self.bbp_win_rate,
            "tie_rate": self.tie_rate,
            "average_score_difference": self.average_score_difference,
            "median_score_difference": self.median_score_difference,
            "max_score_difference": self.max_score_difference,
            "min_score_difference": self.min_score_difference,
            "stddev_score_difference": self.stddev_score_difference,
            "statistical_significance": self.statistical_significance,
            "confidence_level": self.confidence_level,
            "fide_comparison": self.fide_comparison,
            "quality_comparison": self.quality_comparison,
            "size_based_performance": self.size_based_performance,
            "round_based_performance": self.round_based_performance,
            "violation_patterns": self.violation_patterns,
            "performance_stats": self.performance_stats,
        }


class StatisticalAnalyzer:
    """Analyzer for multi-tournament statistical comparison."""

    def __init__(self, min_significance_samples: int = 30):
        """Initialize the statistical analyzer.

        Args:
            min_significance_samples: Minimum samples for statistical significance
        """
        self.min_significance_samples = min_significance_samples
        logger.info("Initialized statistical analyzer")

    def analyze(
        self,
        comparison_results: List[ComparisonResult],
    ) -> StatisticalSummary:
        """Analyze multiple comparison results.

        Args:
            comparison_results: List of individual comparison results

        Returns:
            Comprehensive statistical summary
        """
        if not comparison_results:
            logger.warning("No comparison results to analyze")
            return StatisticalSummary()

        summary = StatisticalSummary()
        summary.total_comparisons = len(comparison_results)

        # Count wins
        for result in comparison_results:
            if result.winner == "gambit":
                summary.gambit_wins += 1
            elif result.winner == "bbp":
                summary.bbp_wins += 1
            else:
                summary.ties += 1

        # Calculate win rates
        if summary.total_comparisons > 0:
            summary.gambit_win_rate = summary.gambit_wins / summary.total_comparisons
            summary.bbp_win_rate = summary.bbp_wins / summary.total_comparisons
            summary.tie_rate = summary.ties / summary.total_comparisons

        # Score difference statistics
        score_diffs = [r.score_difference for r in comparison_results]
        if score_diffs:
            summary.average_score_difference = statistics.mean(score_diffs)
            summary.median_score_difference = statistics.median(score_diffs)
            summary.max_score_difference = max(score_diffs)
            summary.min_score_difference = min(score_diffs)
            if len(score_diffs) > 1:
                summary.stddev_score_difference = statistics.stdev(score_diffs)

        # Calculate statistical significance
        summary.statistical_significance = self._calculate_significance(
            comparison_results
        )
        summary.confidence_level = self._calculate_confidence_level(
            summary.total_comparisons,
            summary.gambit_wins,
            summary.bbp_wins,
        )

        # Detailed comparisons
        summary.fide_comparison = self._compare_fide_scores(comparison_results)
        summary.quality_comparison = self._compare_quality_scores(comparison_results)

        # Performance by characteristics
        summary.size_based_performance = self._analyze_by_tournament_size(
            comparison_results
        )
        summary.round_based_performance = self._analyze_by_round(comparison_results)

        # Violation patterns
        summary.violation_patterns = self._analyze_violation_patterns(
            comparison_results
        )

        # Computational efficiency
        summary.performance_stats = self._analyze_performance(comparison_results)

        logger.info(
            "Analysis complete: %d comparisons, Gambit: %.1f%%, BBP: %.1f%%, Ties: %.1f%%",
            summary.total_comparisons,
            summary.gambit_win_rate * 100,
            summary.bbp_win_rate * 100,
            summary.tie_rate * 100,
        )

        return summary

    def _calculate_significance(
        self,
        results: List[ComparisonResult],
    ) -> float:
        """Calculate statistical significance of results.

        Uses a simple p-value approximation based on sample size and
        win rate difference from 50%.

        Args:
            results: Comparison results

        Returns:
            Significance value (0-1, where >0.95 is highly significant)
        """
        n = len(results)
        if n < self.min_significance_samples:
            return 0.0

        gambit_wins = sum(1 for r in results if r.winner == "gambit")
        win_rate = gambit_wins / n

        # Distance from 50% (no clear winner)
        deviation = abs(win_rate - 0.5)

        # Simple approximation: larger samples and larger deviations = higher significance
        significance = min(1.0, (deviation * 2) * (n / self.min_significance_samples))

        return significance

    def _calculate_confidence_level(
        self,
        total: int,
        gambit_wins: int,
        bbp_wins: int,
    ) -> float:
        """Calculate confidence level in the results.

        Args:
            total: Total comparisons
            gambit_wins: Gambit wins
            bbp_wins: BBP wins

        Returns:
            Confidence level (0-1)
        """
        if total < self.min_significance_samples:
            return 0.5  # Low confidence

        # Higher confidence with more samples and clearer winner
        winner_count = max(gambit_wins, bbp_wins)
        win_percentage = winner_count / total

        # Normalize based on sample size
        sample_factor = min(1.0, total / (self.min_significance_samples * 3))

        # Confidence increases with clear wins
        confidence = 0.5 + (win_percentage - 0.5) * sample_factor

        return min(0.99, max(0.5, confidence))

    def _compare_fide_scores(
        self,
        results: List[ComparisonResult],
    ) -> Dict[str, float]:
        """Compare FIDE compliance scores.

        Args:
            results: Comparison results

        Returns:
            Dictionary with FIDE score comparison statistics
        """
        gambit_scores = []
        bbp_scores = []

        for result in results:
            if result.gambit_metrics:
                gambit_scores.append(result.gambit_metrics.fide_score)
            if result.bbp_metrics:
                bbp_scores.append(result.bbp_metrics.fide_score)

        comparison = {}

        if gambit_scores:
            comparison["gambit_avg_fide"] = statistics.mean(gambit_scores)
            comparison["gambit_median_fide"] = statistics.median(gambit_scores)
            comparison["gambit_min_fide"] = min(gambit_scores)
            comparison["gambit_max_fide"] = max(gambit_scores)

        if bbp_scores:
            comparison["bbp_avg_fide"] = statistics.mean(bbp_scores)
            comparison["bbp_median_fide"] = statistics.median(bbp_scores)
            comparison["bbp_min_fide"] = min(bbp_scores)
            comparison["bbp_max_fide"] = max(bbp_scores)

        if gambit_scores and bbp_scores:
            comparison["fide_difference"] = (
                comparison["gambit_avg_fide"] - comparison["bbp_avg_fide"]
            )

        return comparison

    def _compare_quality_scores(
        self,
        results: List[ComparisonResult],
    ) -> Dict[str, float]:
        """Compare quality metric scores.

        Args:
            results: Comparison results

        Returns:
            Dictionary with quality score comparison statistics
        """
        gambit_scores = []
        bbp_scores = []

        for result in results:
            if result.gambit_metrics:
                gambit_scores.append(result.gambit_metrics.quality_score)
            if result.bbp_metrics:
                bbp_scores.append(result.bbp_metrics.quality_score)

        comparison = {}

        if gambit_scores:
            comparison["gambit_avg_quality"] = statistics.mean(gambit_scores)
            comparison["gambit_median_quality"] = statistics.median(gambit_scores)

        if bbp_scores:
            comparison["bbp_avg_quality"] = statistics.mean(bbp_scores)
            comparison["bbp_median_quality"] = statistics.median(bbp_scores)

        if gambit_scores and bbp_scores:
            comparison["quality_difference"] = (
                comparison["gambit_avg_quality"] - comparison["bbp_avg_quality"]
            )

        return comparison

    def _analyze_by_tournament_size(
        self,
        results: List[ComparisonResult],
    ) -> Dict[str, Dict]:
        """Analyze performance by tournament size.

        Args:
            results: Comparison results

        Returns:
            Dictionary mapping size categories to performance stats
        """
        # Group by size categories
        size_groups = defaultdict(list)

        for result in results:
            # Determine size from pairing count
            num_pairs = len(result.gambit_pairings)

            if num_pairs <= 4:
                size_cat = "small (8-16)"
            elif num_pairs <= 12:
                size_cat = "medium (17-32)"
            else:
                size_cat = "large (33+)"

            size_groups[size_cat].append(result)

        # Analyze each size group
        analysis = {}
        for size_cat, group_results in size_groups.items():
            gambit_wins = sum(1 for r in group_results if r.winner == "gambit")
            bbp_wins = sum(1 for r in group_results if r.winner == "bbp")
            ties = sum(1 for r in group_results if r.winner == "tie")
            total = len(group_results)

            analysis[size_cat] = {
                "total": total,
                "gambit_wins": gambit_wins,
                "bbp_wins": bbp_wins,
                "ties": ties,
                "gambit_win_rate": gambit_wins / total if total > 0 else 0.0,
                "bbp_win_rate": bbp_wins / total if total > 0 else 0.0,
            }

        return dict(analysis)

    def _analyze_by_round(
        self,
        results: List[ComparisonResult],
    ) -> Dict[int, Dict]:
        """Analyze performance by round number.

        Args:
            results: Comparison results

        Returns:
            Dictionary mapping round numbers to performance stats
        """
        round_groups = defaultdict(list)

        for result in results:
            if result.round_number:
                round_groups[result.round_number].append(result)

        analysis = {}
        for round_num, group_results in round_groups.items():
            gambit_wins = sum(1 for r in group_results if r.winner == "gambit")
            bbp_wins = sum(1 for r in group_results if r.winner == "bbp")
            ties = sum(1 for r in group_results if r.winner == "tie")
            total = len(group_results)

            analysis[round_num] = {
                "total": total,
                "gambit_wins": gambit_wins,
                "bbp_wins": bbp_wins,
                "ties": ties,
                "gambit_win_rate": gambit_wins / total if total > 0 else 0.0,
            }

        return analysis

    def _analyze_violation_patterns(
        self,
        results: List[ComparisonResult],
    ) -> Dict[str, Dict]:
        """Analyze common violation patterns.

        Args:
            results: Comparison results

        Returns:
            Dictionary with violation pattern analysis
        """
        gambit_violations = defaultdict(int)
        bbp_violations = defaultdict(int)

        for result in results:
            if result.gambit_metrics and result.gambit_metrics.fide_violations:
                for criterion, count in result.gambit_metrics.fide_violations.items():
                    gambit_violations[criterion] += count

            if result.bbp_metrics and result.bbp_metrics.fide_violations:
                for criterion, count in result.bbp_metrics.fide_violations.items():
                    bbp_violations[criterion] += count

        return {
            "gambit_violations": dict(gambit_violations),
            "bbp_violations": dict(bbp_violations),
            "total_gambit_violations": sum(gambit_violations.values()),
            "total_bbp_violations": sum(bbp_violations.values()),
        }

    def _analyze_performance(
        self,
        results: List[ComparisonResult],
    ) -> Dict[str, float]:
        """Analyze computational performance.

        Args:
            results: Comparison results

        Returns:
            Dictionary with performance statistics
        """
        gambit_times = []
        bbp_times = []

        for result in results:
            if result.gambit_metrics:
                gambit_times.append(result.gambit_metrics.computation_time_ms)
            if result.bbp_metrics:
                bbp_times.append(result.bbp_metrics.computation_time_ms)

        stats = {}

        if gambit_times:
            stats["gambit_avg_time_ms"] = statistics.mean(gambit_times)
            stats["gambit_median_time_ms"] = statistics.median(gambit_times)
            stats["gambit_max_time_ms"] = max(gambit_times)

        if bbp_times:
            stats["bbp_avg_time_ms"] = statistics.mean(bbp_times)
            stats["bbp_median_time_ms"] = statistics.median(bbp_times)
            stats["bbp_max_time_ms"] = max(bbp_times)

        if gambit_times and bbp_times:
            stats["avg_time_difference_ms"] = (
                stats["gambit_avg_time_ms"] - stats["bbp_avg_time_ms"]
            )

        return stats


def create_statistical_analyzer(
    min_significance_samples: int = 30,
) -> StatisticalAnalyzer:
    """Factory function to create a statistical analyzer.

    Args:
        min_significance_samples: Minimum samples for significance

    Returns:
        New StatisticalAnalyzer instance
    """
    return StatisticalAnalyzer(min_significance_samples)
