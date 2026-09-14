# Engine cleanup verification — 2026-09-14

## Integration

BBP v6.0.0 source is now tracked under `vendor/bbp`, including upstream licenses
and tests. The Dutch implementation is `vendor/bbp/src/swisssystems/dutch.cpp`.
`scripts/build_bbp.py --test` compiled and tested it inside the existing Fedora
Toolbox, then staged the binary and license notices for package discovery.
All four upstream C++ tests passed. BBP remains a compiled subprocess; this is
not an in-process C++ binding.

A Linux platform-tagged wheel was built and installed into a temporary target;
its adapter successfully paired four players using the included binary without
configuration. Both BBP license notices and executable permissions were retained.
The source archive includes all upstream C++ sources and excludes binaries.
A clean wheel build from that source archive also succeeded in Toolbox,
automatically compiling BBP from source. Vendored file contents were compared
with the pinned archive and remain unmodified. Other platform builds were not
executed in this Linux environment.

The GUI, generator, comparison and benchmark now share engine discovery.
Ordinary commands need no executable argument. The explicit override remains
available for reference testing. Discovery prefers the packaged engine over
PATH and no longer executes an arbitrary binary from the working directory.

Comparison replay now normalizes generated Player pairs to IDs before replay.
Reports distinguish exact pairing agreement from diagnostic quality scores and
record completed/expected tournament and round counts. `bbp-reference --all`
actually executes the differential suite rather than printing instructions.

## GP changes

- Removed approximately 3,400 lines of unreachable heuristic/fallback code.
- Added provable lower bounds for unavoidable colour-preference violations.
- Added independent NetworkX matching optimization for homogeneous brackets and
  remainders, preserving Dutch exchange/transposition order through exact
  completion costs. With one downfloater, each possible downfloater remains a
  separate candidate for downstream evaluation.
- Fixed omission of repeat-downfloat score differences for MDPs left in limbo.
  This resolves the elite/upset-friendly seed-42 round-five mismatch.

## Results

The repaired CLI compared all 30 rating-distribution/result-pattern combinations,
three tournaments each, seed 42, seven rounds, with player range 16–32 (the
seeded sizes were 19, 16, 24): **90 completed tournaments, 630/630 exact oriented
pairing and bye matches**. No executable arguments or replay failures.

The separate before/after harness using the official BBP v6.0.0 reference binary
also completed all 34 cases with **238/238 matching rounds**. Before this pass,
one small-field round differed and all three larger-field cases timed out.

| Players | GP pairing time, seven rounds | BBP pairing time, seven rounds |
| --- | ---: | ---: |
| 24 | 41 ms | 14 ms |
| 32 | 190 ms | 19 ms |
| 64 | 4.24 s | 53 ms |
| 128 | 27.58 s | 246 ms |

These are single seeded cases, not universal bounds or isolated microbenchmarks.
GP now completes the previous timeout cases, but BBP remains significantly faster
on larger fields. Difficult fields can still exhaust GP's explicit deadline.

The Python suite passed **283 tests**, including 539 differential reference
rounds and exhaustive small-graph checks of optimized candidate ordering.
The CLI reference suite can be run with the built engine, or an independent
binary selected by `GAMBIT_REFERENCE_BBP` when invoking pytest directly.

CLI comparison exit code 2 remains intentional for `not_verified`: independent
global C5–C21 optimality is not proven. Agreement with BBP is regression evidence,
not federation certification. See [rules scope](RULES_COMPLIANCE.md).
