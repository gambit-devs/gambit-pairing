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
from gambitpairing.constants import BYE_SCORE, DRAW_SCORE, LOSS_SCORE, WIN_SCORE
from gambitpairing.player import Player
from gambitpairing.testing.rtg import (
    RandomTournamentGenerator,
    RatingDistribution,
    ResultPattern,
    RTGConfig,
)
from gambitpairing.type_hints import WHITE
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


def _parse_range_value(
    value: str, min_value: int, value_name: str, example_range: str
) -> list[int]:
    """Parse a parameter that can be a single value or range.

    Args:
        value: Value as string (e.g., "24" or "16-64")
        min_value: Minimum allowed value
        value_name: Name of the parameter for error messages
        example_range: Example range for error messages

    Returns:
        [value] for single value, [min, max] for range

    Raises:
        argparse.ArgumentTypeError: If format is invalid
    """
    value = value.strip()

    if "-" in value:
        try:
            parts = value.split("-")
            if len(parts) != 2:
                raise argparse.ArgumentTypeError(
                    f"Invalid range format '{value}'. Use 'MIN-MAX' (e.g., '{example_range}')"
                )

            min_val = int(parts[0].strip())
            max_val = int(parts[1].strip())

            if min_val >= max_val:
                raise argparse.ArgumentTypeError(
                    f"Range minimum ({min_val}) must be less than maximum ({max_val})"
                )

            if min_val < min_value:
                raise argparse.ArgumentTypeError(
                    f"Minimum {value_name} must be at least {min_value}"
                )

            # Sanity check: ensure range is reasonable
            if max_val > 10000:
                raise argparse.ArgumentTypeError(
                    f"Maximum {value_name} ({max_val}) exceeds reasonable limit (10000)"
                )

            return [min_val, max_val]
        except ValueError as e:
            if "invalid literal for int()" in str(e):
                raise argparse.ArgumentTypeError(
                    f"Invalid range '{value}'. Both values must be integers"
                )
            raise argparse.ArgumentTypeError(
                f"Invalid range '{value}'. Both values must be integers: {e}"
            )
    else:
        try:
            val = int(value)
            if val < min_value:
                raise argparse.ArgumentTypeError(
                    f"{value_name.capitalize()} must be at least {min_value}"
                )
            if val > 10000:
                raise argparse.ArgumentTypeError(
                    f"{value_name.capitalize()} ({val}) exceeds reasonable limit (10000)"
                )
            return [val]
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"Invalid {value_name} '{value}'. Must be an integer or range (e.g., '{example_range}')"
            )


def parse_size_range(value: str) -> list[int]:
    """Parse tournament size parameter (single value or range).

    Args:
        value: Size value as string (e.g., "24" or "16-64")

    Returns:
        [size] for single value, [min, max] for range

    Raises:
        argparse.ArgumentTypeError: If format is invalid

    Examples:
        >>> parse_size_range("24")
        [24]
        >>> parse_size_range("16-64")
        [16, 64]
    """
    return _parse_range_value(value, 4, "tournament size", "16-64")


def parse_rounds_range(value: str) -> list[int]:
    """Parse rounds argument (single value or range).

    Args:
        value: Rounds specification (e.g., "7" or "5-9")

    Returns:
        List with single value [N] or range [MIN, MAX]

    Raises:
        argparse.ArgumentTypeError: If format is invalid

    Examples:
        >>> parse_rounds_range("7")
        [7]
        >>> parse_rounds_range("5-9")
        [5, 9]
    """
    return _parse_range_value(value, 1, "rounds", "5-9")


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
    import random

    # Load configuration if provided
    config_dict = load_configuration(args.config)

    # Create output directory
    output_dir = create_output_directory(args.output)

    # Parse size parameter (can be single value or range)
    size_spec = args.size if isinstance(args.size, list) else [args.size]
    is_size_range = len(size_spec) == 2

    # Parse rounds parameter (can be single value or range)
    rounds_spec = args.rounds if isinstance(args.rounds, list) else [args.rounds]
    is_rounds_range = len(rounds_spec) == 2

    # Log comparison setup
    logger.info("Starting comparison of %d tournaments", args.tournaments)

    if is_size_range:
        min_size, max_size = size_spec
        logger.info(
            "Tournament size range: %d-%d players (random for each tournament)",
            min_size,
            max_size,
        )
    else:
        logger.info("Tournament size: %d players", size_spec[0])

    if is_rounds_range:
        min_rounds, max_rounds = rounds_spec
        logger.info(
            "Rounds range: %d-%d rounds (random for each tournament)",
            min_rounds,
            max_rounds,
        )
    else:
        logger.info("Rounds per tournament: %d", rounds_spec[0])

    # Initialize comparison engine
    comparison_engine = PairingComparisonEngine(
        fide_weight=args.fide_weight,
        quality_weight=args.quality_weight,
    )

    # Generate and compare tournaments
    all_results = []

    for i in range(args.tournaments):
        # Determine tournament parameters (random from range or fixed)
        tournament_size = (
            random.randint(size_spec[0], size_spec[1])
            if is_size_range
            else size_spec[0]
        )
        num_rounds = (
            random.randint(rounds_spec[0], rounds_spec[1])
            if is_rounds_range
            else rounds_spec[0]
        )

        logger.info(
            "Generating tournament %d/%d (size: %d, rounds: %d)",
            i + 1,
            args.tournaments,
            tournament_size,
            num_rounds,
        )

        try:
            # Create new RTG for each tournament with different seed
            tournament_seed = args.seed + i if args.seed else None
            tournament_config = RTGConfig(
                num_players=tournament_size,
                num_rounds=num_rounds,
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

                all_snapshot_players, active_players, previous_matches, bye_history = (
                    _build_round_snapshot(players, rounds, round_num)
                )

                # Build player lookup from snapshot players
                snapshot_map = {p.id: p for p in all_snapshot_players}

                # Convert raw pairings (with stale Player objects) to snapshot players
                raw_gambit_pairings = round_data.get("gambit_pairings", [])
                gambit_pairings = _remap_pairings(raw_gambit_pairings, snapshot_map)
                gambit_bye_id = round_data.get("gambit_bye_player_id")
                gambit_bye = snapshot_map.get(gambit_bye_id) if gambit_bye_id else None
                gambit_time = round_data.get("gambit_time_ms", 0.0)

                raw_bbp_pairings = round_data.get("bbp_pairings", [])
                bbp_pairings = _remap_pairings(raw_bbp_pairings, snapshot_map)
                bbp_bye_id = round_data.get("bbp_bye_player_id")
                bbp_bye = snapshot_map.get(bbp_bye_id) if bbp_bye_id else None
                bbp_time = round_data.get("bbp_time_ms", 0.0)

                # Only compare if both pairings exist
                if gambit_pairings and bbp_pairings:
                    result = comparison_engine.compare_pairings(
                        tournament_id=f"tournament_{i+1}",
                        gambit_pairings=gambit_pairings,
                        bbp_pairings=bbp_pairings,
                        gambit_bye=gambit_bye,
                        bbp_bye=bbp_bye,
                        players=active_players,
                        round_number=round_num,
                        total_rounds=args.rounds,
                        gambit_time_ms=gambit_time,
                        bbp_time_ms=bbp_time,
                        previous_matches=previous_matches,
                        player_bye_history=bye_history,
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


def _remap_pairings(
    raw_pairings: list,
    snapshot_map: dict[str, Player],
) -> list[tuple[Player, Player]]:
    """Convert pairings from raw format to snapshot player objects.

    RTG stores pairings as (Player, Player) tuples where the Player objects
    have accumulated all tournament history. For accurate per-round validation,
    we need to remap these to snapshot players that only have history up to
    the current round.

    Args:
        raw_pairings: Pairings as (Player, Player) tuples or (id, id) tuples
        snapshot_map: Mapping from player ID to snapshot Player object

    Returns:
        List of (white, black) Player tuples using snapshot players
    """
    remapped = []
    for pairing in raw_pairings:
        if isinstance(pairing, tuple) and len(pairing) >= 2:
            white_ref, black_ref = pairing[0], pairing[1]
            # Handle both Player objects and ID strings
            white_id = white_ref.id if hasattr(white_ref, "id") else white_ref
            black_id = black_ref.id if hasattr(black_ref, "id") else black_ref
            white = snapshot_map.get(white_id)
            black = snapshot_map.get(black_id)
            if white and black:
                remapped.append((white, black))
    return remapped


def _create_fresh_player(source_player) -> Player:
    """Create a fresh player with static attributes but empty history.

    Args:
        source_player: Source player object or dict to copy attributes from

    Returns:
        New Player instance with empty history lists
    """
    if isinstance(source_player, Player):
        data = source_player.to_dict()
    else:
        data = dict(source_player)

    # Create player with only static attributes
    fresh = Player(
        name=data.get("name", "Unknown"),
        rating=data.get("rating"),
    )

    # Copy static identification attributes
    fresh.id = data.get("id", fresh.id)
    fresh.pairing_number = data.get("pairing_number")
    fresh.club = data.get("club")
    fresh.federation = data.get("federation")
    fresh.gender = data.get("gender")
    fresh.title = data.get("title")
    fresh.fide_id = data.get("fide_id")

    # Reset all history to empty (critical for accurate round-by-round validation)
    fresh.opponent_ids = []
    fresh.results = []
    fresh.color_history = []
    fresh.running_scores = []
    fresh.float_history = []
    fresh.match_history = []
    fresh.has_received_bye = False
    fresh.num_black_games = 0
    fresh.is_active = data.get("is_active", True)
    fresh.points = 0.0

    return fresh


def _build_round_snapshot(
    players: list,
    rounds: list,
    round_number: int,
) -> tuple[list[Player], list[Player], set, dict]:
    player_map: dict[str, Player] = {}
    for player in players:
        player_obj = _create_fresh_player(player)
        player_map[player_obj.id] = player_obj

    previous_matches: set = set()
    bye_history: dict[str, int] = {}

    rounds_sorted = sorted(rounds, key=lambda r: r.get("round_number", 0))
    for round_data in rounds_sorted:
        current_round = round_data.get("round_number", 0)
        if current_round >= round_number:
            break

        pairing_ids = round_data.get("pairings", [])
        results = round_data.get("results", [])
        results_map: dict[tuple[str, str], tuple[float, float]] = {}
        for result in results:
            if isinstance(result, dict):
                white_id = result.get("white_id")
                black_id = result.get("black_id")
                white_score = result.get("white_score")
                black_score = result.get("black_score")
            else:
                white_id, black_id = result[0], result[1]
                white_score = result[2] if len(result) > 2 else None
                black_score = result[3] if len(result) > 3 else None
                forfeit = result[4] if len(result) > 4 else False
                if black_score is None and white_score is not None:
                    if forfeit and float(white_score) == LOSS_SCORE:
                        black_score = LOSS_SCORE
                    else:
                        black_score = WIN_SCORE - float(white_score)

            if white_id and black_id and white_score is not None:
                if black_score is None:
                    black_score = WIN_SCORE - float(white_score)
                results_map[(white_id, black_id)] = (
                    float(white_score),
                    float(black_score),
                )

        for white_id, black_id in pairing_ids:
            if white_id not in player_map or black_id not in player_map:
                continue
            scores = results_map.get((white_id, black_id))
            if scores is None:
                continue
            white_score, black_score = scores
            white_player = player_map[white_id]
            black_player = player_map[black_id]
            white_player.add_round_result(black_player, white_score, WHITE)
            black_player.add_round_result(white_player, black_score, BLACK)
            previous_matches.add(frozenset({white_id, black_id}))

        bye_id = round_data.get("bye_player_id") or round_data.get("bye_player")
        if bye_id and bye_id in player_map:
            player_map[bye_id].add_round_result(None, BYE_SCORE, None)
            bye_history[bye_id] = bye_history.get(bye_id, 0) + 1

        scheduled_byes = round_data.get("scheduled_byes", {})
        for half_id in scheduled_byes.get("half_point", []):
            if half_id in player_map:
                player_map[half_id].add_round_result(None, DRAW_SCORE, None)
        for zero_id in scheduled_byes.get("zero_point", []):
            if zero_id in player_map:
                player_map[zero_id].add_round_result(None, LOSS_SCORE, None)

    excluded_ids = set()
    for round_data in rounds_sorted:
        if round_data.get("round_number", 0) != round_number:
            continue
        scheduled_byes = round_data.get("scheduled_byes", {})
        excluded_ids |= set(scheduled_byes.get("half_point", []))
        excluded_ids |= set(scheduled_byes.get("zero_point", []))
        break

    active_players = [
        player
        for player_id, player in player_map.items()
        if player_id not in excluded_ids
    ]

    return list(player_map.values()), active_players, previous_matches, bye_history


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

  # Random size from range for each tournament
  gambit-compare --tournaments 100 --size 16-64 --rounds 5

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
        type=parse_size_range,
        default=[24],
        help="Number of players per tournament (default: 24). Use range like '16-64' to randomly select size for each tournament",
    )

    parser.add_argument(
        "--rounds",
        type=parse_rounds_range,
        default=[7],
        help="Number of rounds per tournament (default: 7). Use range like '5-9' to randomly select rounds for each tournament",
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
