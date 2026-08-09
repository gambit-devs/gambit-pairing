"""Comprehensive JSON reporting for comparison results.

This module provides JSON report generation with detailed comparison data,
statistics, and analysis suitable for technical evaluation.
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

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from gambitpairing.comparison.analyzer import StatisticalSummary
from gambitpairing.comparison.engine import ComparisonResult
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


class ComparisonReporter:
    """Reporter for generating comprehensive comparison reports."""

    def __init__(
        self,
        fide_weight: float = 0.7,
        quality_weight: float = 0.3,
    ):
        """Initialize the reporter.

        Args:
            fide_weight: Weight for FIDE compliance
            quality_weight: Weight for quality metrics
        """
        self.fide_weight = fide_weight
        self.quality_weight = quality_weight

    def generate_report(
        self,
        comparison_results: List[ComparisonResult],
        statistical_summary: StatisticalSummary,
        configuration: Optional[Dict] = None,
    ) -> Dict:
        """Generate comprehensive comparison report.

        Args:
            comparison_results: List of individual comparison results
            statistical_summary: Statistical analysis summary
            configuration: Optional configuration metadata

        Returns:
            Complete report as dictionary
        """
        report = {
            "comparison_metadata": self._generate_metadata(
                len(comparison_results),
                configuration,
            ),
            "overall_results": self._generate_overall_results(statistical_summary),
            "detailed_analysis": self._generate_detailed_analysis(statistical_summary),
            "tournament_breakdown": self._generate_tournament_breakdown(
                comparison_results
            ),
            "pairing_difference_analysis": self._generate_pairing_analysis(
                comparison_results
            ),
            "performance_comparison": self._generate_performance_comparison(
                statistical_summary
            ),
        }

        return report

    def save_report(
        self,
        report: Dict,
        output_path: Path,
        pretty: bool = True,
    ) -> None:
        """Save report to JSON file.

        Args:
            report: Report dictionary
            output_path: Path to save JSON file
            pretty: Whether to pretty-print JSON
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            if pretty:
                json.dump(report, f, indent=2, ensure_ascii=False)
            else:
                json.dump(report, f, ensure_ascii=False)

        logger.info("Report saved to: %s", output_path)

    def _generate_metadata(
        self,
        total_tournaments: int,
        configuration: Optional[Dict],
    ) -> Dict:
        """Generate metadata section.

        Args:
            total_tournaments: Total tournaments compared
            configuration: Configuration used

        Returns:
            Metadata dictionary
        """
        metadata = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_tournaments": total_tournaments,
            "scoring_weights": {
                "fide_compliance": self.fide_weight,
                "quality": self.quality_weight,
            },
            "report_version": "1.0.0",
        }

        if configuration:
            metadata["configuration"] = configuration

        return metadata

    def _generate_overall_results(
        self,
        summary: StatisticalSummary,
    ) -> Dict:
        """Generate overall results section.

        Args:
            summary: Statistical summary

        Returns:
            Overall results dictionary
        """
        # Determine overall winner
        if summary.gambit_win_rate > summary.bbp_win_rate:
            winner = "gambit"
        elif summary.bbp_win_rate > summary.gambit_win_rate:
            winner = "bbp"
        else:
            winner = "tie"

        return {
            "winner": winner,
            "gambit_win_rate": round(summary.gambit_win_rate, 4),
            "bbp_win_rate": round(summary.bbp_win_rate, 4),
            "tie_rate": round(summary.tie_rate, 4),
            "total_comparisons": summary.total_comparisons,
            "gambit_wins": summary.gambit_wins,
            "bbp_wins": summary.bbp_wins,
            "ties": summary.ties,
            "average_score_difference": round(summary.average_score_difference, 2),
            "median_score_difference": round(summary.median_score_difference, 2),
            "max_score_difference": round(summary.max_score_difference, 2),
            "stddev_score_difference": round(summary.stddev_score_difference, 2),
            "statistical_significance": round(summary.statistical_significance, 4),
            "confidence_level": round(summary.confidence_level, 4),
        }

    def _generate_detailed_analysis(
        self,
        summary: StatisticalSummary,
    ) -> Dict:
        """Generate detailed analysis section.

        Args:
            summary: Statistical summary

        Returns:
            Detailed analysis dictionary
        """
        analysis = {
            "fide_comparison": {
                k: round(v, 2) for k, v in summary.fide_comparison.items()
            },
            "quality_metrics": {
                k: round(v, 2) for k, v in summary.quality_comparison.items()
            },
            "size_based_performance": self._format_size_performance(
                summary.size_based_performance
            ),
            "round_based_analysis": self._format_round_performance(
                summary.round_based_performance
            ),
            "violation_patterns": summary.violation_patterns,
        }

        return analysis

    def _generate_tournament_breakdown(
        self,
        results: List[ComparisonResult],
    ) -> List[Dict]:
        """Generate tournament-by-tournament breakdown.

        Args:
            results: Comparison results

        Returns:
            List of tournament summaries
        """
        breakdown = []

        for result in results:
            entry = {
                "tournament_id": result.tournament_id,
                "round_number": result.round_number,
                "winner": result.winner,
                "score_difference": round(result.score_difference, 2),
            }

            if result.gambit_metrics:
                entry["gambit"] = {
                    "overall_score": round(result.gambit_metrics.overall_score, 2),
                    "fide_score": round(result.gambit_metrics.fide_score, 2),
                    "quality_score": round(result.gambit_metrics.quality_score, 2),
                    "violations": result.gambit_metrics.fide_violations,
                    "computation_time_ms": round(
                        result.gambit_metrics.computation_time_ms, 2
                    ),
                }

            if result.bbp_metrics:
                entry["bbp"] = {
                    "overall_score": round(result.bbp_metrics.overall_score, 2),
                    "fide_score": round(result.bbp_metrics.fide_score, 2),
                    "quality_score": round(result.bbp_metrics.quality_score, 2),
                    "violations": result.bbp_metrics.fide_violations,
                    "computation_time_ms": round(
                        result.bbp_metrics.computation_time_ms, 2
                    ),
                }

            if result.pairing_differences:
                entry["pairing_differences"] = result.pairing_differences.to_dict()

            breakdown.append(entry)

        return breakdown

    def _generate_pairing_analysis(
        self,
        results: List[ComparisonResult],
    ) -> Dict:
        """Generate pairing difference analysis.

        Args:
            results: Comparison results

        Returns:
            Pairing analysis dictionary
        """
        total_matching = 0
        total_different = 0
        total_color_different = 0
        total_comparisons = 0

        for result in results:
            if result.pairing_differences:
                total_matching += result.pairing_differences.matching_pairs
                total_different += len(
                    result.pairing_differences.gambit_only_pairs
                ) + len(result.pairing_differences.bbp_only_pairs)
                total_color_different += len(
                    result.pairing_differences.different_colors
                )
                total_comparisons += 1

        total_pairs = total_matching + total_different

        return {
            "total_comparisons": total_comparisons,
            "total_matching_pairs": total_matching,
            "total_different_pairs": total_different,
            "total_color_differences": total_color_different,
            "overall_matching_percentage": round(
                (total_matching / total_pairs * 100) if total_pairs > 0 else 0, 2
            ),
            "average_matching_per_tournament": round(
                total_matching / total_comparisons if total_comparisons > 0 else 0, 2
            ),
            "average_differences_per_tournament": round(
                total_different / total_comparisons if total_comparisons > 0 else 0, 2
            ),
        }

    def _generate_performance_comparison(
        self,
        summary: StatisticalSummary,
    ) -> Dict:
        """Generate computational performance comparison.

        Args:
            summary: Statistical summary

        Returns:
            Performance comparison dictionary
        """
        performance = {}

        for key, value in summary.performance_stats.items():
            performance[key] = round(value, 2)

        # Add performance winner
        if "gambit_avg_time_ms" in performance and "bbp_avg_time_ms" in performance:
            if performance["gambit_avg_time_ms"] < performance["bbp_avg_time_ms"]:
                performance["faster_engine"] = "gambit"
                performance["speed_advantage_ms"] = round(
                    performance["bbp_avg_time_ms"] - performance["gambit_avg_time_ms"],
                    2,
                )
            else:
                performance["faster_engine"] = "bbp"
                performance["speed_advantage_ms"] = round(
                    performance["gambit_avg_time_ms"] - performance["bbp_avg_time_ms"],
                    2,
                )

        return performance

    def _format_size_performance(
        self,
        size_performance: Dict[str, Dict],
    ) -> Dict[str, Dict]:
        """Format size-based performance data.

        Args:
            size_performance: Raw size performance data

        Returns:
            Formatted size performance
        """
        formatted = {}

        for size_cat, stats in size_performance.items():
            formatted[size_cat] = {
                "total": stats["total"],
                "gambit_wins": stats["gambit_wins"],
                "bbp_wins": stats["bbp_wins"],
                "ties": stats["ties"],
                "gambit_win_rate": round(stats["gambit_win_rate"], 4),
                "bbp_win_rate": round(stats["bbp_win_rate"], 4),
            }

        return formatted

    def _format_round_performance(
        self,
        round_performance: Dict[int, Dict],
    ) -> Dict[str, Dict]:
        """Format round-based performance data.

        Args:
            round_performance: Raw round performance data

        Returns:
            Formatted round performance (with string keys for JSON)
        """
        formatted = {}

        for round_num, stats in round_performance.items():
            formatted[f"round_{round_num}"] = {
                "total": stats["total"],
                "gambit_wins": stats["gambit_wins"],
                "bbp_wins": stats["bbp_wins"],
                "ties": stats["ties"],
                "gambit_win_rate": round(stats["gambit_win_rate"], 4),
            }

        return formatted


def generate_comprehensive_report(
    comparison_results: List[ComparisonResult],
    statistical_summary: StatisticalSummary,
    output_path: Optional[Path] = None,
    configuration: Optional[Dict] = None,
    fide_weight: float = 0.7,
    quality_weight: float = 0.3,
) -> Dict:
    """Generate and optionally save comprehensive comparison report.

    Args:
        comparison_results: List of comparison results
        statistical_summary: Statistical analysis
        output_path: Optional path to save report
        configuration: Optional configuration metadata
        fide_weight: FIDE compliance weight
        quality_weight: Quality metrics weight

    Returns:
        Complete report dictionary
    """
    reporter = ComparisonReporter(fide_weight, quality_weight)
    report = reporter.generate_report(
        comparison_results,
        statistical_summary,
        configuration,
    )

    if output_path:
        reporter.save_report(report, output_path)

    return report
