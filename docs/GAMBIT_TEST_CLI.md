# Gambit Test CLI - Unified Documentation

## Overview

`gambit-test` is a unified command-line interface for testing and validating the Gambit Pairing system. It supports interactive and direct command modes, making it versatile for developers, tournament organizers, and researchers.

## Features

- **Interactive Mode**: Full-featured shell with autocomplete and command discovery.
- **Direct Command Mode**: Execute specific commands directly from the terminal.
- **Multiple Testing Types**: Generate, compare, validate, benchmark, and run unit tests.
- **FIDE Compliance Validation**: Ensure tournaments meet FIDE standards.
- **Performance Benchmarking**: Compare pairing engines and analyze performance.

## Installation

Install Gambit Pairing and the CLI tool:

```bash
python install_editable_pip.py
```

## Quick Start

### Interactive Mode

Launch the interactive shell:

```bash
gambit-test
```

- Type `/help` to see all commands.
- Use TAB for autocomplete.
- Type `exit` or `quit` to leave.

### Direct Command Mode

Run commands directly:

```bash
gambit-test generate --players 32 --rounds 7 --validate
```

## Commands

### 1. Generate Tournaments

Generate realistic tournaments for testing.

```bash
gambit-test generate [OPTIONS]
```

**Options:**
- `--players N|MIN-MAX`: Number of players (default: 24). Specify a fixed number `N` or a range `MIN-MAX` (e.g., `16-32`). For ranges, each tournament will randomly select a size within the range.
- `--rounds N|MIN-MAX`: Number of rounds (default: 7). Specify a fixed number `N` or a range `MIN-MAX` (e.g., `5-9`). For ranges, each tournament will randomly select rounds within the range.
- `--tournaments N`: Number of tournaments to generate (default: 1). When combined with ranges, generates multiple tournaments with varying parameters.
- `--distribution TYPE`: Rating distribution (e.g., `uniform`, `normal`, `fide`).
- `--pattern TYPE`: Result pattern (e.g., `realistic`, `balanced`, `upset_friendly`).
- `--pairing-system TYPE`: Pairing system (e.g., `dutch_swiss`, `bbp_dutch`, `dual`).
- `--seed N`: Random seed for reproducibility.
- `--output FILE`: Save to file. For multiple tournaments, files will be numbered.
- `--format TYPE`: Output format (`json` or `trf`).
- `--validate`: Validate FIDE compliance.

**Examples:**
```bash
# Generate single tournament with fixed parameters
gambit-test generate --players 24 --rounds 7

# Generate 10 tournaments with varying sizes and rounds
gambit-test generate --players 16-32 --rounds 5-9 --tournaments 10

# Generate and validate with seed
gambit-test generate --players 24 --rounds 7 --validate --seed 42
```

### 2. Compare Engines

Compare Gambit and BBP pairing engines.

```bash
gambit-test compare --tournaments N [OPTIONS]
```

**Options:**
- `--tournaments N`: Number of tournaments to compare (default: 50).
- `--size N|MIN-MAX`: Players per tournament (default: 24). Specify a fixed number `N` or a range `MIN-MAX` (e.g., `16-64`). For ranges, each tournament will randomly select a size within the range.
- `--rounds N|MIN-MAX`: Rounds per tournament (default: 7). Specify a fixed number `N` or a range `MIN-MAX` (e.g., `5-9`). For ranges, each tournament will randomly select rounds within the range.
- `--distribution TYPE`: Rating distribution pattern.
- `--pattern TYPE`: Result generation pattern.
- `--seed N`: Random seed for reproducibility.
- `--fide-weight FLOAT`: FIDE compliance weight (default: 0.7).
- `--quality-weight FLOAT`: Quality metrics weight (default: 0.3).
- `--output DIR`: Save results.
- `--bbp-executable PATH`: Path to BBP executable.

**Examples:**
```bash
# Compare with fixed parameters
gambit-test compare --tournaments 50 --size 24 --rounds 7

# Compare with varying tournament sizes and rounds
gambit-test compare --tournaments 100 --size 16-64 --rounds 5-9

# Compare with specific distribution and pattern
gambit-test compare --tournaments 50 --distribution elite --pattern balanced
```

### 3. Validate Tournaments

Validate tournament files against FIDE standards.

```bash
gambit-test validate --file FILE [OPTIONS]
```

**Options:**
- `--file FILE`: Tournament file to validate.
- `--detailed`: Show detailed violations.
- `--export FILE`: Save validation report.

### 4. Run Unit Tests

Run unit tests for Gambit Pairing.

```bash
gambit-test unit [OPTIONS]
```

**Options:**
- `--module MODULE`: Test specific module (e.g., `dutch`, `all`).
- `--verbose`: Detailed output.
- `--coverage`: Generate coverage report.

### 5. Benchmark Performance

Benchmark pairing engine performance.

```bash
gambit-test benchmark [OPTIONS]
```

**Options:**
- `--size N`: Tournament size.
- `--iterations N`: Number of iterations.
- `--compare-bbp`: Include BBP engine.

## Examples

### Generate Single Tournament

```bash
# Generate single tournament with fixed parameters
gambit-test generate --players 32 --rounds 7 --validate
```

### Generate Multiple Tournaments with Ranges

```bash
# Generate 20 tournaments with varying sizes (16-48 players) and rounds (5-9)
gambit-test generate --players 16-48 --rounds 5-9 --tournaments 20 --seed 42

# Generate and save to files (creates output_1.json, output_2.json, etc.)
gambit-test generate --players 16-32 --rounds 5-7 --tournaments 5 --output tournament.json
```

### Compare Engines with Fixed Parameters

```bash
# Compare 100 tournaments with fixed size and rounds
gambit-test compare --tournaments 100 --size 32 --rounds 7
```

### Compare Engines with Ranges

```bash
# Compare 50 tournaments with varying sizes (16-64 players) and rounds (5-9)
gambit-test compare --tournaments 50 --size 16-64 --rounds 5-9

# Compare with specific distribution and pattern
gambit-test compare --tournaments 100 --size 24-48 --rounds 7-9 --distribution elite --pattern balanced
```

### Validate Tournament

```bash
gambit-test validate --file tournament.json --detailed
```

### Run All Unit Tests

```bash
gambit-test unit --module all --coverage
```

### Benchmark Performance

```bash
gambit-test benchmark --size 64 --iterations 20
```

## Tips

1. Use `--seed` for reproducible results.
2. Organize outputs with `--output`.
3. Use `/help` in interactive mode for guidance.

## Support

For full documentation, visit the [Gambit Pairing GitHub](https://github.com/gambit-devs/gambit-pairing/issues).
