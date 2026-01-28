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
gambit-test generate --players N --rounds N [OPTIONS]
```

**Options:**
- `--players N`: Number of players (default: 24).
- `--rounds N`: Number of rounds (default: 7).
- `--distribution TYPE`: Rating distribution (e.g., `uniform`, `normal`, `fide`).
- `--output FILE`: Save to file.
- `--validate`: Validate FIDE compliance.

### 2. Compare Engines

Compare Gambit and BBP pairing engines.

```bash
gambit-test compare --tournaments N [OPTIONS]
```

**Options:**
- `--tournaments N`: Number of tournaments (default: 50).
- `--size N`: Players per tournament.
- `--fide-weight FLOAT`: FIDE compliance weight.
- `--output DIR`: Save results.

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

### Generate and Validate

```bash
gambit-test generate --players 32 --rounds 7 --validate
```

### Compare Engines

```bash
gambit-test compare --tournaments 100 --size 32
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
