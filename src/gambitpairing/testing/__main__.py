"""Unified Testing CLI for Gambit Pairing.

This module provides a comprehensive, interactive command-line interface
for all testing functionality in Gambit Pairing.
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
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import NestedCompleter, WordCompleter
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.styles import Style

    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

from gambitpairing.comparison.cli import parse_size_range
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


# ANSI color codes for terminal output
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    DARK_GREEN = "\033[32m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def show_loading_animation():
    """Display a scrolling ASCII art loading animation."""
    loading_file = Path(__file__).parent / "loading"
    if not loading_file.exists():
        return

    try:
        with open(loading_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Clear screen and hide cursor
        print("\033[2J\033[H\033[?25l", end="")

        for line in lines:
            print(f"{Colors.DARK_GREEN}{line.rstrip()}{Colors.ENDC}")
            time.sleep(0.05)  # Adjust speed as needed

        # Show cursor again
        print("\033[?25h", end="")
        time.sleep(0.5)  # Brief pause before banner

    except Exception as e:
        logger.warning(f"Could not display loading animation: {e}")


# Command definitions with their options
COMMANDS = {
    "generate": {
        "description": "Generate random tournaments (RTG)",
        "options": {
            "--players": "Number of players (default: 24)",
            "--rounds": "Number of rounds (default: 7)",
            "--distribution": "Rating distribution (uniform/normal/skewed/elite/club/fide)",
            "--pattern": "Result pattern (realistic/balanced/upset_friendly/predictable/random)",
            "--seed": "Random seed for reproducibility",
            "--pairing-system": "Pairing system (dutch_swiss/bbp_dutch/dual)",
            "--output": "Output file path",
            "--format": "Output format (json/trf)",
            "--validate": "Run FIDE validation",
        },
    },
    "compare": {
        "description": "Compare Gambit vs BBP pairing engines",
        "options": {
            "--tournaments": "Number of tournaments to compare (default: 50)",
            "--size": "Players per tournament (default: 24, or range like 16-64 for random selection)",
            "--rounds": "Rounds per tournament (default: 7)",
            "--distribution": "Rating distribution",
            "--pattern": "Result pattern",
            "--seed": "Random seed",
            "--fide-weight": "FIDE compliance weight (default: 0.7)",
            "--quality-weight": "Quality metrics weight (default: 0.3)",
            "--output": "Output directory",
            "--bbp-executable": "Path to BBP executable",
        },
    },
    "validate": {
        "description": "Validate tournament FIDE compliance",
        "options": {
            "--file": "Tournament file to validate (JSON)",
            "--round": "Specific round to validate",
            "--detailed": "Show detailed violation information",
            "--export": "Export validation report (json/txt)",
        },
    },
    "unit": {
        "description": "Run unit tests (pytest)",
        "options": {
            "--module": "Specific module to test (dutch/roundrobin/all)",
            "--verbose": "Verbose output",
            "--coverage": "Generate coverage report",
            "--markers": "Run tests with specific markers",
        },
    },
    "bbp-reference": {
        "description": "Run BBP reference tests",
        "options": {
            "--path": "Path to BBP executable",
            "--test-case": "Specific test case to run",
            "--all": "Run all reference tests",
        },
    },
    "benchmark": {
        "description": "Performance benchmarking",
        "options": {
            "--size": "Tournament size to benchmark (default: 24, or range like 16-64 for random)",
            "--rounds": "Number of rounds (default: 7)",
            "--iterations": "Number of iterations (default: 10)",
            "--compare-bbp": "Include BBP in benchmark",
        },
    },
    "help": {
        "description": "Show help for specific command",
        "options": {
            "<command>": "Command name to get help for",
        },
    },
    "exit": {"description": "Exit the interactive mode", "options": {}},
}


def print_banner():
    """Print the application banner."""
    banner = f"""
{Colors.OKBLUE}╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║                     GAMBIT TEST - CLI                         ║
║                                                               ║
║                 [Every test in one place]                     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝{Colors.ENDC}

Type {Colors.BOLD}/help{Colors.ENDC} to see all available commands
Type {Colors.BOLD}exit{Colors.ENDC} or {Colors.BOLD}quit{Colors.ENDC} to leave interactive mode
"""
    print(banner)


def print_commands_list():
    """Print list of all available commands."""
    print(f"\n{Colors.BOLD}Available Commands:{Colors.ENDC}\n")
    for cmd, info in COMMANDS.items():
        print(f"  {Colors.OKGREEN}{cmd:15}{Colors.ENDC} - {info['description']}")
    print()


def print_command_help(command: str):
    """Print detailed help for a specific command."""
    if command not in COMMANDS:
        print(f"{Colors.FAIL}Unknown command: {command}{Colors.ENDC}")
        print_commands_list()
        return

    cmd_info = COMMANDS[command]
    print(f"\n{Colors.BOLD}{Colors.OKBLUE}Command: {command}{Colors.ENDC}")
    print(f"{Colors.BOLD}Description:{Colors.ENDC} {cmd_info['description']}\n")

    if cmd_info["options"]:
        print(f"{Colors.BOLD}Options:{Colors.ENDC}")
        for option, description in cmd_info["options"].items():
            print(f"  {Colors.OKCYAN}{option:20}{Colors.ENDC} {description}")
    print()


def create_completer():
    """Create autocomplete completer for interactive mode."""
    if not PROMPT_TOOLKIT_AVAILABLE:
        return None

    # Build nested completer from commands
    # Support both "/command" and "command" formats
    completions = {}
    for cmd, info in COMMANDS.items():
        options_completer = (
            WordCompleter(list(info["options"].keys())) if info["options"] else None
        )
        # Add both with and without "/" prefix
        completions[cmd] = options_completer
        completions[f"/{cmd}"] = options_completer

    # Add special meta-commands
    completions["/help"] = None
    completions["/list"] = None

    return NestedCompleter.from_nested_dict(completions)


def run_generate_command(args: argparse.Namespace) -> int:
    """Run the generate (RTG) command."""
    from gambitpairing.testing.rtg import (
        RandomTournamentGenerator,
        RatingDistribution,
        ResultPattern,
        RTGConfig,
    )

    print(f"\n{Colors.BOLD}Generating tournament...{Colors.ENDC}")

    # Convert string enums
    distribution = (
        RatingDistribution[args.distribution.upper()]
        if args.distribution
        else RatingDistribution.NORMAL
    )
    pattern = (
        ResultPattern[args.pattern.upper()] if args.pattern else ResultPattern.REALISTIC
    )

    # Create config
    config = RTGConfig(
        num_players=args.players,
        num_rounds=args.rounds,
        rating_distribution=distribution,
        result_pattern=pattern,
        pairing_system=args.pairing_system or "dutch_swiss",
        seed=args.seed,
        validate_with_fpc=args.validate,
    )
    if args.validate:
        config.fide_strict = True

    # Generate tournament
    rtg = RandomTournamentGenerator(config)
    tournament_data = rtg.generate_complete_tournament()

    # Export if requested
    if args.output:
        output_path = Path(args.output)
        if args.format == "json":
            content = rtg.export_json_format(tournament_data)
            output_path.write_text(content, encoding="utf-8")
        elif args.format == "trf":
            content = rtg.export_trf_format(tournament_data)
            output_path.write_text(content, encoding="utf-8")

        print(f"{Colors.OKGREEN}Tournament saved to: {output_path}{Colors.ENDC}")

    # Print summary
    print(f"\n{Colors.BOLD}Tournament Generated:{Colors.ENDC}")
    print(f"  Players: {len(tournament_data['players'])}")
    print(f"  Rounds: {len(tournament_data['rounds'])}")

    if "fpc_report" in tournament_data:
        report = tournament_data["fpc_report"]
        print(f"\n{Colors.BOLD}FIDE Compliance:{Colors.ENDC}")

        # Show violation counts if any
        num_violations = len(report.get("absolute_violations", []))
        num_warnings = len(report.get("warnings", []))

        if num_violations > 0:
            print(f"  {Colors.FAIL}Absolute violations: {num_violations}{Colors.ENDC}")
            violation_ids = report.get("absolute_violations", [])
            if violation_ids:
                print(f"    Criteria: {' '.join(violation_ids)}")

        if num_warnings > 0:
            print(f"  {Colors.WARNING}Quality warnings: {num_warnings}{Colors.ENDC}")

        # Show summary
        print(f"  {report.get('summary', 'N/A')}")

    return 0


def run_compare_command(args: argparse.Namespace) -> int:
    """Run the comparison command."""
    from gambitpairing.comparison.cli import run_comparison

    print(f"\n{Colors.BOLD}Running comparison analysis...{Colors.ENDC}")
    return run_comparison(args)


def run_validate_command(args: argparse.Namespace) -> int:
    """Run the validation command."""
    import json

    from gambitpairing.validation.fpc import create_fpc_validator

    if not args.file:
        print(f"{Colors.FAIL}Error: --file required{Colors.ENDC}")
        return 1

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"{Colors.FAIL}Error: File not found: {file_path}{Colors.ENDC}")
        return 1

    print(f"\n{Colors.BOLD}Validating tournament: {file_path}{Colors.ENDC}")

    # Load tournament data
    with open(file_path, "r", encoding="utf-8") as f:
        tournament_data = json.load(f)

    # Validate
    validator = create_fpc_validator()
    report = validator.validate_tournament_compliance(tournament_data)

    # Print results
    print(f"\n{Colors.BOLD}Validation Results:{Colors.ENDC}")
    print(f"  Compliance: {report.compliance_percentage:.1f}%")
    print(f"  Summary: {report.summary}")

    if args.detailed:
        print(f"\n{Colors.BOLD}Violations:{Colors.ENDC}")
        for violation in report.violations:
            print(f"  - {violation.criterion_id}: {violation.message}")

    # Export if requested
    if args.export:
        export_path = Path(args.export)
        if export_path.suffix == ".json":
            export_data = {
                "compliance_percentage": report.compliance_percentage,
                "summary": report.summary,
                "violations": [
                    {
                        "criterion": v.criterion_id,
                        "status": v.status.value,
                        "message": v.message,
                    }
                    for v in report.violations
                ],
            }
            export_path.write_text(json.dumps(export_data, indent=2), encoding="utf-8")
        else:
            export_path.write_text(report.summary, encoding="utf-8")

        print(f"\n{Colors.OKGREEN}Report exported to: {export_path}{Colors.ENDC}")

    return 0


def run_unit_command(args: argparse.Namespace) -> int:
    """Run unit tests using pytest."""
    import subprocess

    print(f"\n{Colors.BOLD}Running unit tests...{Colors.ENDC}")

    pytest_args = ["pytest"]

    if args.module:
        if args.module == "dutch":
            pytest_args.append("tests/test_fide_dutch.py")
        elif args.module == "all":
            pytest_args.append("tests/")
        else:
            pytest_args.append(f"tests/test_{args.module}.py")
    else:
        pytest_args.append("tests/")

    if args.verbose:
        pytest_args.append("-v")

    if args.coverage:
        pytest_args.extend(["--cov=gambitpairing", "--cov-report=html"])

    if args.markers:
        pytest_args.extend(["-m", args.markers])

    result = subprocess.run(pytest_args)
    return result.returncode


def run_bbp_reference_command(args: argparse.Namespace) -> int:
    """Run BBP reference tests."""
    print(f"\n{Colors.BOLD}Running BBP reference tests...{Colors.ENDC}")
    print(f"{Colors.WARNING}BBP reference tests require C++ compilation{Colors.ENDC}")
    print(f"Location: bbpPairings-dutch-2025/test/")

    if args.all:
        print("\nTo run all BBP tests:")
        print("  cd bbpPairings-dutch-2025/test && make test")
    else:
        print("\nTo run BBP tests:")
        print("  cd bbpPairings-dutch-2025/test && make")

    return 0


def run_benchmark_command(args: argparse.Namespace) -> int:
    """Run performance benchmarks."""
    import time

    from gambitpairing.testing.rtg import (
        RandomTournamentGenerator,
        RatingDistribution,
        ResultPattern,
        RTGConfig,
    )

    print(f"\n{Colors.BOLD}Running performance benchmark...{Colors.ENDC}")
    print(f"Tournament size: {args.size} players, {args.rounds} rounds")
    print(f"Iterations: {args.iterations}\n")

    times = []

    for i in range(args.iterations):
        config = RTGConfig(
            num_players=args.size,
            num_rounds=args.rounds,
            rating_distribution=RatingDistribution.NORMAL,
            result_pattern=ResultPattern.REALISTIC,
            pairing_system="dual" if args.compare_bbp else "dutch_swiss",
            seed=42 + i,
        )

        rtg = RandomTournamentGenerator(config)
        start = time.perf_counter()
        rtg.generate_complete_tournament()
        elapsed = time.perf_counter() - start
        times.append(elapsed)

        print(f"  Iteration {i+1}/{args.iterations}: {elapsed*1000:.2f}ms")

    # Statistics
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    print(f"\n{Colors.BOLD}Results:{Colors.ENDC}")
    print(f"  Average: {avg_time*1000:.2f}ms")
    print(f"  Min: {min_time*1000:.2f}ms")
    print(f"  Max: {max_time*1000:.2f}ms")

    return 0


def run_interactive_mode():
    """Run in interactive mode with autocomplete."""
    if not PROMPT_TOOLKIT_AVAILABLE:
        print(f"{Colors.FAIL}Error: prompt_toolkit not installed{Colors.ENDC}")
        print("Install with: pip install prompt_toolkit")
        print("\nFalling back to standard mode...")
        return run_standard_mode()

    show_loading_animation()
    print_banner()

    # Create session with autocomplete
    style = Style.from_dict(
        {
            "prompt": "#00aa00 bold",
        }
    )

    session = PromptSession(
        completer=create_completer(),
        history=InMemoryHistory(),
        style=style,
    )

    while True:
        try:
            # Get user input
            user_input = session.prompt("gambit-test> ").strip()

            if not user_input:
                continue

            # Handle special commands
            if user_input in ["exit", "quit", "q"]:
                print(f"\n{Colors.OKGREEN}Goodbye!{Colors.ENDC}\n")
                break

            if user_input in ["/help", "help", "?"]:
                print_commands_list()
                continue

            if user_input in ["/list"]:
                print_commands_list()
                continue

            if user_input.startswith("/help ") or user_input.startswith("help "):
                cmd = user_input.split()[1].lstrip("/")
                print_command_help(cmd)
                continue

            # Parse and execute command
            parts = user_input.split()
            if not parts:
                continue

            # Strip leading "/" if present (support both "/command" and "command")
            command = parts[0].lstrip("/")

            if command not in COMMANDS:
                print(f"{Colors.FAIL}Unknown command: {command}{Colors.ENDC}")
                print(f"Type {Colors.BOLD}/help{Colors.ENDC} to see available commands")
                continue

            # Build argument list
            args_list = parts[1:]

            # Execute command
            try:
                if command == "generate":
                    parser = create_generate_parser()
                    args = parser.parse_args(args_list)
                    run_generate_command(args)
                elif command == "compare":
                    parser = create_compare_parser()
                    args = parser.parse_args(args_list)
                    run_compare_command(args)
                elif command == "validate":
                    parser = create_validate_parser()
                    args = parser.parse_args(args_list)
                    run_validate_command(args)
                elif command == "unit":
                    parser = create_unit_parser()
                    args = parser.parse_args(args_list)
                    run_unit_command(args)
                elif command == "bbp-reference":
                    parser = create_bbp_parser()
                    args = parser.parse_args(args_list)
                    run_bbp_reference_command(args)
                elif command == "benchmark":
                    parser = create_benchmark_parser()
                    args = parser.parse_args(args_list)
                    run_benchmark_command(args)
                elif command == "help":
                    if args_list:
                        print_command_help(args_list[0])
                    else:
                        print_commands_list()

            except SystemExit:
                # argparse calls sys.exit on error, catch it
                continue
            except Exception as e:
                print(f"{Colors.FAIL}Error: {e}{Colors.ENDC}")
                logger.exception("Command execution failed")

        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}Use 'exit' or 'quit' to leave{Colors.ENDC}")
        except EOFError:
            print(f"\n{Colors.OKGREEN}Goodbye!{Colors.ENDC}\n")
            break


def run_standard_mode():
    """Run in standard CLI mode (non-interactive)."""
    parser = create_main_parser()
    args = parser.parse_args()

    if args.interactive:
        return run_interactive_mode()

    # Execute subcommand
    if hasattr(args, "func"):
        return args.func(args)
    else:
        parser.print_help()
        return 0


def create_generate_parser():
    """Create parser for generate subcommand."""
    parser = argparse.ArgumentParser(description="Generate random tournaments")
    parser.add_argument("--players", type=int, default=24, help="Number of players")
    parser.add_argument("--rounds", type=int, default=7, help="Number of rounds")
    parser.add_argument(
        "--distribution",
        choices=["uniform", "normal", "skewed", "elite", "club", "fide"],
        default="normal",
        help="Rating distribution",
    )
    parser.add_argument(
        "--pattern",
        choices=["realistic", "balanced", "upset_friendly", "predictable", "random"],
        default="realistic",
        help="Result pattern",
    )
    parser.add_argument("--seed", type=int, help="Random seed")
    parser.add_argument(
        "--pairing-system",
        choices=["dutch_swiss", "bbp_dutch", "dual"],
        default="dutch_swiss",
        help="Pairing system",
    )
    parser.add_argument("--output", help="Output file path")
    parser.add_argument(
        "--format", choices=["json", "trf"], default="json", help="Output format"
    )
    parser.add_argument("--validate", action="store_true", help="Run FIDE validation")
    return parser


def create_compare_parser():
    """Create parser for compare subcommand."""
    parser = argparse.ArgumentParser(description="Compare Gambit vs BBP")
    parser.add_argument(
        "--tournaments", type=int, default=50, help="Number of tournaments"
    )
    parser.add_argument(
        "--size",
        type=parse_size_range,
        default=[24],
        help="Players per tournament. Use range like '16-64' to randomly select size for each tournament",
    )
    parser.add_argument("--rounds", type=int, default=7, help="Rounds per tournament")
    parser.add_argument(
        "--distribution",
        choices=["uniform", "normal", "skewed", "elite", "club", "fide"],
        default="normal",
        help="Rating distribution",
    )
    parser.add_argument(
        "--pattern",
        choices=["realistic", "balanced", "upset_friendly", "predictable", "random"],
        default="realistic",
        help="Result pattern",
    )
    parser.add_argument("--seed", type=int, help="Random seed")
    parser.add_argument(
        "--fide-weight", type=float, default=0.7, help="FIDE compliance weight"
    )
    parser.add_argument(
        "--quality-weight", type=float, default=0.3, help="Quality metrics weight"
    )
    parser.add_argument("--output", help="Output directory")
    parser.add_argument("--bbp-executable", help="Path to BBP executable")
    parser.add_argument("--fide-strict", action="store_true", help="Strict FIDE mode")
    parser.add_argument("--keep-bbp-files", action="store_true", help="Keep BBP files")
    parser.add_argument(
        "--min-significance", type=int, default=30, help="Min samples for significance"
    )
    parser.add_argument("--config", help="Config file")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


def create_validate_parser():
    """Create parser for validate subcommand."""
    parser = argparse.ArgumentParser(description="Validate FIDE compliance")
    parser.add_argument("--file", required=True, help="Tournament file (JSON)")
    parser.add_argument("--round", type=int, help="Specific round to validate")
    parser.add_argument(
        "--detailed", action="store_true", help="Show detailed violations"
    )
    parser.add_argument("--export", help="Export report (json/txt)")
    return parser


def create_unit_parser():
    """Create parser for unit test subcommand."""
    parser = argparse.ArgumentParser(description="Run unit tests")
    parser.add_argument(
        "--module", choices=["dutch", "roundrobin", "all"], help="Specific module"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--coverage", action="store_true", help="Generate coverage report"
    )
    parser.add_argument("--markers", help="Run tests with specific markers")
    return parser


def create_bbp_parser():
    """Create parser for BBP reference tests."""
    parser = argparse.ArgumentParser(description="Run BBP reference tests")
    parser.add_argument("--path", help="Path to BBP executable")
    parser.add_argument("--test-case", help="Specific test case")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    return parser


def create_benchmark_parser():
    """Create parser for benchmark subcommand."""
    parser = argparse.ArgumentParser(description="Performance benchmarking")
    parser.add_argument("--size", type=int, default=24, help="Tournament size")
    parser.add_argument("--rounds", type=int, default=7, help="Number of rounds")
    parser.add_argument(
        "--iterations", type=int, default=10, help="Number of iterations"
    )
    parser.add_argument(
        "--compare-bbp", action="store_true", help="Include BBP in benchmark"
    )
    return parser


def create_main_parser():
    """Create main argument parser."""
    parser = argparse.ArgumentParser(
        prog="gambit-test",
        description="Unified testing CLI for Gambit Pairing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  gambit-test

  # Generate tournament
  gambit-test generate --players 24 --rounds 7

  # Compare engines
  gambit-test compare --tournaments 50

  # Validate tournament
  gambit-test validate --file tournament.json

  # Run unit tests
  gambit-test unit --module dutch --verbose

  # Benchmark performance
  gambit-test benchmark --size 64 --iterations 20
        """,
    )

    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Start in interactive mode"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Generate subcommand
    gen_parser = subparsers.add_parser("generate", help="Generate random tournaments")
    gen_parser.add_argument("--players", type=int, default=24)
    gen_parser.add_argument("--rounds", type=int, default=7)
    gen_parser.add_argument(
        "--distribution",
        choices=["uniform", "normal", "skewed", "elite", "club", "fide"],
        default="normal",
    )
    gen_parser.add_argument(
        "--pattern",
        choices=["realistic", "balanced", "upset_friendly", "predictable", "random"],
        default="realistic",
    )
    gen_parser.add_argument("--seed", type=int)
    gen_parser.add_argument(
        "--pairing-system",
        choices=["dutch_swiss", "bbp_dutch", "dual"],
        default="dutch_swiss",
    )
    gen_parser.add_argument("--output")
    gen_parser.add_argument("--format", choices=["json", "trf"], default="json")
    gen_parser.add_argument("--validate", action="store_true")
    gen_parser.set_defaults(func=run_generate_command)

    # Compare subcommand
    cmp_parser = subparsers.add_parser("compare", help="Compare Gambit vs BBP")
    cmp_parser.add_argument("--tournaments", type=int, default=50)
    cmp_parser.add_argument("--size", type=int, default=24)
    cmp_parser.add_argument("--rounds", type=int, default=7)
    cmp_parser.add_argument(
        "--distribution",
        choices=["uniform", "normal", "skewed", "elite", "club", "fide"],
        default="normal",
    )
    cmp_parser.add_argument(
        "--pattern",
        choices=["realistic", "balanced", "upset_friendly", "predictable", "random"],
        default="realistic",
    )
    cmp_parser.add_argument("--seed", type=int)
    cmp_parser.add_argument("--fide-weight", type=float, default=0.7)
    cmp_parser.add_argument("--quality-weight", type=float, default=0.3)
    cmp_parser.add_argument("--output")
    cmp_parser.add_argument("--bbp-executable")
    cmp_parser.add_argument("--fide-strict", action="store_true")
    cmp_parser.add_argument("--keep-bbp-files", action="store_true")
    cmp_parser.add_argument("--min-significance", type=int, default=30)
    cmp_parser.add_argument("--config")
    cmp_parser.add_argument("--verbose", action="store_true")
    cmp_parser.set_defaults(func=run_compare_command)

    # Validate subcommand
    val_parser = subparsers.add_parser("validate", help="Validate FIDE compliance")
    val_parser.add_argument("--file", required=True)
    val_parser.add_argument("--round", type=int)
    val_parser.add_argument("--detailed", action="store_true")
    val_parser.add_argument("--export")
    val_parser.set_defaults(func=run_validate_command)

    # Unit test subcommand
    unit_parser = subparsers.add_parser("unit", help="Run unit tests")
    unit_parser.add_argument("--module", choices=["dutch", "roundrobin", "all"])
    unit_parser.add_argument("--verbose", action="store_true")
    unit_parser.add_argument("--coverage", action="store_true")
    unit_parser.add_argument("--markers")
    unit_parser.set_defaults(func=run_unit_command)

    # BBP reference subcommand
    bbp_parser = subparsers.add_parser("bbp-reference", help="Run BBP reference tests")
    bbp_parser.add_argument("--path")
    bbp_parser.add_argument("--test-case")
    bbp_parser.add_argument("--all", action="store_true")
    bbp_parser.set_defaults(func=run_bbp_reference_command)

    # Benchmark subcommand
    bench_parser = subparsers.add_parser("benchmark", help="Performance benchmarking")
    bench_parser.add_argument("--size", type=int, default=24)
    bench_parser.add_argument("--rounds", type=int, default=7)
    bench_parser.add_argument("--iterations", type=int, default=10)
    bench_parser.add_argument("--compare-bbp", action="store_true")
    bench_parser.set_defaults(func=run_benchmark_command)

    return parser


def main() -> int:
    """Main entry point for gambit-test CLI."""
    # If no arguments, start interactive mode
    if len(sys.argv) == 1:
        return run_interactive_mode()

    # Check for interactive flag
    if "--interactive" in sys.argv or "-i" in sys.argv:
        return run_interactive_mode()

    # Otherwise run standard mode
    return run_standard_mode()


if __name__ == "__main__":
    sys.exit(main())
