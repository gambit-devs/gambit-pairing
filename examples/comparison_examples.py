"""Example script demonstrating the Gambit vs BBP comparison system.

This script shows how to use the comparison features both programmatically
and via the command-line interface.
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

import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gambitpairing.comparison.analyzer import create_statistical_analyzer
from gambitpairing.comparison.directory_utils import create_comparison_session
from gambitpairing.comparison.engine import PairingComparisonEngine
from gambitpairing.comparison.reporter import generate_comprehensive_report
from gambitpairing.testing.rtg import (
    RandomTournamentGenerator,
    RatingDistribution,
    ResultPattern,
    RTGConfig,
)


def example_programmatic_comparison():
    """Example: Using the comparison system programmatically."""

    print("\n" + "=" * 70)
    print("EXAMPLE 1: Programmatic Comparison")
    print("=" * 70 + "\n")

    # Create a comparison session
    session_dir = create_comparison_session("example_comparison")
    print(f"Created comparison session: {session_dir}\n")

    # Configure the tournament generator for dual pairing mode
    rtg_config = RTGConfig(
        num_players=16,
        num_rounds=5,
        rating_distribution=RatingDistribution.NORMAL,
        result_pattern=ResultPattern.REALISTIC,
        pairing_system="dual",  # Generate both Gambit and BBP pairings
        bbp_workdir=str(session_dir / "bbp_files"),
        validate_with_fpc=True,
        seed=42,
    )

    print("Generating 3 tournaments with dual pairings...")

    # Initialize comparison engine
    comparison_engine = PairingComparisonEngine(
        fide_weight=0.7,
        quality_weight=0.3,
    )

    # Generate tournaments and collect comparisons
    all_results = []

    for i in range(3):
        print(f"\nTournament {i+1}:")

        # Create RTG and generate tournament
        rtg = RandomTournamentGenerator(rtg_config)
        tournament_data = rtg.generate()

        players = tournament_data["players"]
        rounds = tournament_data["rounds"]

        print(f"  Generated {len(players)} players, {len(rounds)} rounds")

        # Compare each round
        for round_data in rounds:
            gambit_pairings = round_data.get("gambit_pairings", [])
            bbp_pairings = round_data.get("bbp_pairings", [])

            if gambit_pairings and bbp_pairings:
                result = comparison_engine.compare_pairings(
                    tournament_id=f"tournament_{i+1}",
                    gambit_pairings=gambit_pairings,
                    bbp_pairings=bbp_pairings,
                    gambit_bye=None,
                    bbp_bye=None,
                    players=players,
                    round_number=round_data["round_number"],
                    total_rounds=len(rounds),
                    gambit_time_ms=round_data.get("gambit_time_ms", 0),
                    bbp_time_ms=round_data.get("bbp_time_ms", 0),
                )
                all_results.append(result)
                print(f"  Round {round_data['round_number']}: {result.winner} wins")

    # Analyze results
    print(f"\n\nAnalyzing {len(all_results)} comparison results...")
    analyzer = create_statistical_analyzer()
    statistical_summary = analyzer.analyze(all_results)

    # Generate report
    report_path = session_dir / "reports" / "comparison_report.json"

    configuration = {
        "tournaments": 3,
        "size": 16,
        "rounds": 5,
        "distribution": "normal",
        "pattern": "realistic",
    }

    report = generate_comprehensive_report(
        comparison_results=all_results,
        statistical_summary=statistical_summary,
        output_path=report_path,
        configuration=configuration,
    )

    # Print summary
    print("\n" + "=" * 70)
    print("COMPARISON SUMMARY")
    print("=" * 70)
    print(f"Total Comparisons: {statistical_summary.total_comparisons}")
    print(
        f"Gambit Wins: {statistical_summary.gambit_wins} ({statistical_summary.gambit_win_rate*100:.1f}%)"
    )
    print(
        f"BBP Wins: {statistical_summary.bbp_wins} ({statistical_summary.bbp_win_rate*100:.1f}%)"
    )
    print(f"Ties: {statistical_summary.ties} ({statistical_summary.tie_rate*100:.1f}%)")
    print(f"\nReport saved to: {report_path}")
    print("=" * 70 + "\n")


def example_cli_usage():
    """Example: Show CLI usage examples."""

    print("\n" + "=" * 70)
    print("EXAMPLE 2: Command-Line Interface Usage")
    print("=" * 70 + "\n")

    print("After installing the package with pip install -e ., you can use:")
    print("\n1. Basic comparison with 50 tournaments:")
    print("   $ gambit-compare --tournaments 50")

    print("\n2. Large tournaments with custom parameters:")
    print("   $ gambit-compare --tournaments 100 --size 64 --rounds 9")

    print("\n3. Custom scoring weights (80% FIDE, 20% Quality):")
    print("   $ gambit-compare --fide-weight 0.8 --quality-weight 0.2")

    print("\n4. Specify output directory:")
    print("   $ gambit-compare --output my_comparison_results")

    print("\n5. Use specific BBP executable:")
    print("   $ gambit-compare --bbp-executable /path/to/bbp")

    print("\n6. FIDE strict mode:")
    print("   $ gambit-compare --fide-strict --tournaments 100")

    print("\n7. Different rating distributions and result patterns:")
    print("   $ gambit-compare --distribution elite --pattern balanced")

    print("\n8. Reproducible results with seed:")
    print("   $ gambit-compare --seed 42 --tournaments 50")

    print("\n9. Load configuration from file:")
    print("   $ gambit-compare --config comparison_config.json")

    print("\n10. Help:")
    print("    $ gambit-compare --help")

    print("\n" + "=" * 70 + "\n")


def example_integration_workflow():
    """Example: Complete workflow for tournament organizers."""

    print("\n" + "=" * 70)
    print("EXAMPLE 3: Complete Workflow for Tournament Organizers")
    print("=" * 70 + "\n")

    print("Step 1: Evaluate which pairing engine is best for your tournament")
    print("  $ gambit-compare --size 32 --rounds 7 --tournaments 100")
    print("  This generates 100 test tournaments and comprehensively compares")
    print("  Gambit and BBP pairings based on:")
    print("    - FIDE compliance (70% weight)")
    print("    - Quality metrics (30% weight)")

    print("\nStep 2: Review the comprehensive JSON report")
    print(
        "  Location: src/gambitpairing/testing/bbp_pairings/[timestamp]_comparison/comparison_report.json"
    )
    print("  The report includes:")
    print("    - Overall winner and win rates")
    print("    - FIDE compliance scores")
    print("    - Quality metrics comparison")
    print("    - Tournament-by-tournament breakdown")
    print("    - Pairing difference analysis")
    print("    - Performance statistics")

    print("\nStep 3: Understand the metrics")
    print("  - Overall Score = (FIDE Score × 0.7) + (Quality Score × 0.3)")
    print("  - FIDE Score: Based on violations of FIDE criteria C1-C21")
    print("  - Quality Score: PSD, color balance, bracket compliance, etc.")

    print("\nStep 4: Make informed decision")
    print("  - If Gambit wins: Use Gambit for better FIDE compliance")
    print("  - If BBP wins: BBP may provide better overall pairing quality")
    print("  - Check size-based performance for your specific tournament size")
    print("  - Review round-by-round analysis for specific round patterns")

    print("\n" + "=" * 70 + "\n")


def example_advanced_analysis():
    """Example: Advanced analysis features."""

    print("\n" + "=" * 70)
    print("EXAMPLE 4: Advanced Analysis Features")
    print("=" * 70 + "\n")

    print("The comparison system provides detailed analysis:")

    print("\n1. Tournament Size Analysis:")
    print("   - Small (8-16 players)")
    print("   - Medium (17-32 players)")
    print("   - Large (33+ players)")
    print("   Shows which engine performs better at different scales")

    print("\n2. Round-by-Round Analysis:")
    print("   - Performance in early rounds (Round 1-3)")
    print("   - Performance in middle rounds")
    print("   - Performance in final rounds")
    print("   Identifies if one engine is better for specific rounds")

    print("\n3. Violation Pattern Analysis:")
    print("   - Common violations by criterion (C1-C21)")
    print("   - Unique violations per engine")
    print("   - Total violation counts")

    print("\n4. Pairing Difference Analysis:")
    print("   - Percentage of matching pairs")
    print("   - Player pairs that differ between engines")
    print("   - Color assignment differences")
    print("   - Impact on tournament outcomes")

    print("\n5. Performance Benchmarking:")
    print("   - Average pairing generation time")
    print("   - Memory usage patterns")
    print("   - Scalability analysis")

    print("\n6. Statistical Significance:")
    print("   - Confidence levels")
    print("   - P-values for win rate differences")
    print("   - Minimum sample sizes for significance")

    print("\n" + "=" * 70 + "\n")


def main():
    """Run all examples."""

    print("\n" + "╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  GAMBIT vs BBP PAIRING COMPARISON SYSTEM - EXAMPLES".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")

    # Show all examples
    example_cli_usage()
    example_integration_workflow()
    example_advanced_analysis()

    # Optionally run programmatic example (commented out by default)
    # Uncomment to actually run a comparison:
    # example_programmatic_comparison()

    print("\n" + "=" * 70)
    print("To run a real comparison, uncomment example_programmatic_comparison()")
    print("or use the gambit-compare CLI tool")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
