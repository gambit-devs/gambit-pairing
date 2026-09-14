# Program structure of Gambit Pairing

## Backend and presentation boundaries

- `src/gambitpairing/models/`: player, configuration, match and round data.
- `controllers/tournament/`: session, recording/undo, canonical replay, standings,
  and isolated pairing jobs. These modules do not import Qt.
- `controllers/pairing/dutch_swiss.py`: native GP entry point and colour/float rules.
- `controllers/pairing/strict_dutch.py`: bracket search and ordered criteria.
- `controllers/pairing/matching.py`: exact matching bounds and deterministic
  candidate selection; independent of BBP.
- `controllers/pairing/bbp_dutch.py`: production BBP adapter and shared discovery.
- `compatibility/bbp.py`: TRF conversion and pairing-output parsing.
- `representation/`: validated document loading and reconstruction.
- `validation/`: absolute rule checks and explicitly incomplete quality verification.
- `testing/` and `comparison/`: generators, benchmarks and comparison reports.
- `gui/`: Qt presentation and interaction; sporting ranks come from the backend.

Pairing workers receive document snapshots. Results are checked against the
unchanged session before commit. Save/load and simulation share canonical replay.

## Third-party source and builds

The BBP C++ source is tracked in `vendor/bbp/`, with the Dutch algorithm in
`vendor/bbp/src/swisssystems/dutch.cpp`. It is not an in-process Python extension:
Gambit launches a bundled executable through its adapter.

`scripts/build_bbp.py --test` builds BBP, runs its upstream tests, and stages the
binary and license notices in `src/gambitpairing/resources/bin/`. The GUI and CLI
use the same automatic discovery. See [vendor instructions](../vendor/README.md).

See [rules and verification](RULES_COMPLIANCE.md) for supported rules and limits.
