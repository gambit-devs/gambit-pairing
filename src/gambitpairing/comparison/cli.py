"""Command-line interface for pairing comparison tool.

This module provides CLI functionality for the standalone comparison tool.
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

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from gambitpairing.comparison.analyzer import create_statistical_analyzer
from gambitpairing.comparison.engine import PairingComparisonEngine
from gambitpairing.comparison.reporter import generate_comprehensive_report
from gambitpairing.testing.rtg import (
    RandomTournamentGenerator,
    RatingDistribution,
    ResultPattern,
    RTGConfig,
)
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


def create_output_directory(base_path: Optional[str] = None) -> Path:
    """Create output directory for comparison results.

    Args:
        base_path: Optional base path (defaults to src/gambitpairing/testing/bbp_pairings/)

    Returns:
        Path to output directory
    """
    if base_path:
        output_dir = Path(base_path)
    else:
        # Default: src/gambitpairing/testing/bbp_pairings/[timestamp]_comparison/
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = (
            Path("src")
            / "gambitpairing"
            / "testing"
            / "bbp_pairings"
            / f"{timestamp}_comparison"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Output directory: %s", output_dir)

    return output_dir


def load_configuration(config_file: Optional[str]) -> Optional[dict]:
    """Load configuration from JSON file.

    Args:
        config_file: Path to configuration file

    Returns:
        Configuration dictionary or None
    """
    if not config_file:
        return None

    config_path = Path(config_file)
    if not config_path.exists():
        logger.error("Configuration file not found: %s", config_file)
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        logger.info("Loaded configuration from: %s", config_file)
        return config
    except Exception as e:
        logger.error("Failed to load configuration: %s", e)
        return None


def run_comparison(args: argparse.Namespace) -> int:
    """Run the comparison based on CLI arguments.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    # Load configuration if provided
    config_dict = load_configuration(args.config)

    # Create output directory
    output_dir = create_output_directory(args.output)

    # Setup RTG configuration
    rtg_config = RTGConfig(
        num_players=args.size,
        num_rounds=args.rounds,
        rating_distribution=RatingDistribution[args.distribution.upper()],
        result_pattern=ResultPattern[args.pattern.upper()],
        pairing_system="dual",  # Use dual mode for comparison
        bbp_executable=args.bbp_executable,
        bbp_workdir=str(output_dir / "bbp_files"),
        bbp_keep_files=args.keep_bbp_files,
        validate_with_fpc=True,
        fide_strict=args.fide_strict,
        seed=args.seed,
    )

    logger.info("Starting comparison of %d tournaments", args.tournaments)
    logger.info("Tournament size: %d players, %d rounds", args.size, args.rounds)

    # Initialize comparison engine
    comparison_engine = PairingComparisonEngine(
        fide_weight=args.fide_weight,
        quality_weight=args.quality_weight,
    )

    # Generate and compare tournaments
    all_results = []

    for i in range(args.tournaments):
        logger.info("Generating tournament %d/%d", i + 1, args.tournaments)

        try:
            # Create new RTG for each tournament with different seed
            tournament_seed = args.seed + i if args.seed else None
            tournament_config = RTGConfig(
                num_players=args.size,
                num_rounds=args.rounds,
                rating_distribution=RatingDistribution[args.distribution.upper()],
                result_pattern=ResultPattern[args.pattern.upper()],
                pairing_system="dual",
                bbp_executable=args.bbp_executable,
                bbp_workdir=str(output_dir / "bbp_files"),
                bbp_keep_files=args.keep_bbp_files,
                validate_with_fpc=True,
                fide_strict=args.fide_strict,
                seed=tournament_seed,
            )

            rtg = RandomTournamentGenerator(tournament_config)
            tournament_data = rtg.generate_complete_tournament()

            # Extract players and rounds
            players = tournament_data["players"]
            rounds = tournament_data["rounds"]

            # Compare each round
            for round_data in rounds:
                round_num = round_data["round_number"]

                # Get Gambit pairings
                gambit_pairings = round_data.get("gambit_pairings", [])
                gambit_bye_id = round_data.get("gambit_bye_player_id")
                gambit_bye = (
                    next((p for p in players if p.id == gambit_bye_id), None)
                    if gambit_bye_id
                    else None
                )
                gambit_time = round_data.get("gambit_time_ms", 0.0)

                # Get BBP pairings
                bbp_pairings = round_data.get("bbp_pairings", [])
                bbp_bye_id = round_data.get("bbp_bye_player_id")
                bbp_bye = (
                    next((p for p in players if p.id == bbp_bye_id), None)
                    if bbp_bye_id
                    else None
                )
                bbp_time = round_data.get("bbp_time_ms", 0.0)

                # Only compare if both pairings exist
                if gambit_pairings and bbp_pairings:
                    result = comparison_engine.compare_pairings(
                        tournament_id=f"tournament_{i+1}",
                        gambit_pairings=gambit_pairings,
                        bbp_pairings=bbp_pairings,
                        gambit_bye=gambit_bye,
                        bbp_bye=bbp_bye,
                        players=players,
                        round_number=round_num,
                        total_rounds=args.rounds,
                        gambit_time_ms=gambit_time,
                        bbp_time_ms=bbp_time,
                    )
                    all_results.append(result)

            logger.info("Tournament %d: compared %d rounds", i + 1, len(rounds))

        except Exception as e:
            logger.error(
                "Failed to generate tournament %d: %s", i + 1, e, exc_info=True
            )
            continue

    # Analyze results
    if not all_results:
        logger.error(
            "No comparison results generated - check BBP executable configuration"
        )
        return 1

    logger.info("Analyzing %d comparison results", len(all_results))
    analyzer = create_statistical_analyzer(
        min_significance_samples=args.min_significance
    )
    statistical_summary = analyzer.analyze(all_results)

    # Generate report
    report_path = output_dir / "comparison_report.json"

    configuration_metadata = {
        "tournaments": args.tournaments,
        "size": args.size,
        "rounds": args.rounds,
        "distribution": args.distribution,
        "pattern": args.pattern,
        "fide_strict": args.fide_strict,
        "seed": args.seed,
        "scoring_weights": {
            "fide": args.fide_weight,
            "quality": args.quality_weight,
        },
    }

    if config_dict:
        configuration_metadata["custom_config"] = config_dict

    report = generate_comprehensive_report(
        comparison_results=all_results,
        statistical_summary=statistical_summary,
        output_path=report_path,
        configuration=configuration_metadata,
        fide_weight=args.fide_weight,
        quality_weight=args.quality_weight,
    )

    # Print summary to console
    print_summary(statistical_summary, report_path)

    logger.info("Comparison complete!")
    return 0


def print_summary(summary, report_path: Path) -> None:
    """Print comparison summary to console.

    Args:
        summary: Statistical summary
        report_path: Path to full report
    """
    print("\n" + "=" * 70)
    print("GAMBIT vs BBP PAIRING COMPARISON SUMMARY")
    print("=" * 70)

    print(f"\nTotal Comparisons: {summary.total_comparisons}")
    print(f"  Gambit Wins: {summary.gambit_wins} ({summary.gambit_win_rate*100:.1f}%)")
    print(f"  BBP Wins: {summary.bbp_wins} ({summary.bbp_win_rate*100:.1f}%)")
    print(f"  Ties: {summary.ties} ({summary.tie_rate*100:.1f}%)")

    # Determine overall winner
    if summary.gambit_win_rate > summary.bbp_win_rate:
        winner = "GAMBIT"
        advantage = (summary.gambit_win_rate - summary.bbp_win_rate) * 100
    elif summary.bbp_win_rate > summary.gambit_win_rate:
        winner = "BBP"
        advantage = (summary.bbp_win_rate - summary.gambit_win_rate) * 100
    else:
        winner = "TIE"
        advantage = 0

    print(f"\nOverall Winner: {winner}")
    if advantage > 0:
        print(f"Win Rate Advantage: {advantage:.1f}%")

    print(f"\nAverage Score Difference: {summary.average_score_difference:.2f}")
    print(f"Statistical Significance: {summary.statistical_significance:.2%}")
    print(f"Confidence Level: {summary.confidence_level:.2%}")

    # FIDE Compliance
    if summary.fide_comparison:
        print("\nFIDE Compliance Scores:")
        gambit_fide = summary.fide_comparison.get("gambit_avg_fide", 0)
        bbp_fide = summary.fide_comparison.get("bbp_avg_fide", 0)
        print(f"  Gambit Average: {gambit_fide:.2f}/100")
        print(f"  BBP Average: {bbp_fide:.2f}/100")
        print(f"  Difference: {gambit_fide - bbp_fide:+.2f}")

    # Quality Metrics
    if summary.quality_comparison:
        print("\nQuality Scores:")
        gambit_quality = summary.quality_comparison.get("gambit_avg_quality", 0)
        bbp_quality = summary.quality_comparison.get("bbp_avg_quality", 0)
        print(f"  Gambit Average: {gambit_quality:.2f}/100")
        print(f"  BBP Average: {bbp_quality:.2f}/100")
        print(f"  Difference: {gambit_quality - bbp_quality:+.2f}")

    # Performance
    if summary.performance_stats:
        print("\nComputational Performance:")
        gambit_time = summary.performance_stats.get("gambit_avg_time_ms", 0)
        bbp_time = summary.performance_stats.get("bbp_avg_time_ms", 0)
        print(f"  Gambit Average: {gambit_time:.2f}ms")
        print(f"  BBP Average: {bbp_time:.2f}ms")
        if gambit_time > 0 and bbp_time > 0:
            if gambit_time < bbp_time:
                print(f"  Gambit is {bbp_time/gambit_time:.2f}x faster")
            else:
                print(f"  BBP is {gambit_time/bbp_time:.2f}x faster")

    print("\n" + "=" * 70)
    print(f"Full report saved to: {report_path}")
    print("=" * 70 + "\n")


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI.

    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="Compare Gambit and BBP pairing engines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic comparison with 50 tournaments
  gambit-compare --tournaments 50

  # Large tournaments with custom parameters
  gambit-compare --tournaments 100 --size 64 --rounds 9

  # Custom scoring weights
  gambit-compare --fide-weight 0.8 --quality-weight 0.2

  # Use configuration file
  gambit-compare --config comparison_config.json

  # Specify BBP executable
  gambit-compare --bbp-executable /path/to/bbp
        """,
    )

    # Basic options
    parser.add_argument(
        "--tournaments",
        type=int,
        default=50,
        help="Number of tournaments to generate and compare (default: 50)",
    )

    parser.add_argument(
        "--size",
        type=int,
        default=24,
        help="Number of players per tournament (default: 24)",
    )

    parser.add_argument(
        "--rounds",
        type=int,
        default=7,
        help="Number of rounds per tournament (default: 7)",
    )

    # Tournament generation options
    parser.add_argument(
        "--distribution",
        choices=["uniform", "normal", "skewed", "elite", "club", "fide"],
        default="normal",
        help="Rating distribution pattern (default: normal)",
    )

    parser.add_argument(
        "--pattern",
        choices=["realistic", "balanced", "upset_friendly", "predictable", "random"],
        default="realistic",
        help="Result generation pattern (default: realistic)",
    )

    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")

    # BBP options
    parser.add_argument("--bbp-executable", help="Path to BBP executable")

    parser.add_argument(
        "--keep-bbp-files",
        action="store_true",
        help="Keep temporary BBP files after comparison",
    )

    # Scoring weights
    parser.add_argument(
        "--fide-weight",
        type=float,
        default=0.7,
        help="Weight for FIDE compliance (default: 0.7)",
    )

    parser.add_argument(
        "--quality-weight",
        type=float,
        default=0.3,
        help="Weight for quality metrics (default: 0.3)",
    )

    # Analysis options
    parser.add_argument(
        "--min-significance",
        type=int,
        default=30,
        help="Minimum samples for statistical significance (default: 30)",
    )

    parser.add_argument(
        "--fide-strict", action="store_true", help="Use strict FIDE compliance mode"
    )

    # Output options
    parser.add_argument(
        "--output",
        help="Output directory for results (default: src/gambitpairing/testing/bbp_pairings/[timestamp])",
    )

    parser.add_argument("--config", help="Load configuration from JSON file")

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    return parser


def main() -> int:
    """Main entry point for CLI.

    Returns:
        Exit code
    """
    parser = create_parser()
    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        import logging

        logging.getLogger().setLevel(logging.DEBUG)

    try:
        return run_comparison(args)
    except KeyboardInterrupt:
        logger.info("Comparison interrupted by user")
        return 130
    except Exception as e:
        logger.error("Comparison failed: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
