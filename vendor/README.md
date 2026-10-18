# Third-party engines

## BBP Pairings

`bbp/` is the unmodified upstream BBP Pairings v6.0.0 source, including its Apache-2.0 license and regression tests.

- Upstream: https://github.com/BieremaBoyzProgramming/bbpPairings/tree/v6.0.0
- Archive SHA-256: `b7f95c0803131e38a56e8829bd062d9ad51908322dd6fef01380b2f612f58227`

## Building

From the project root, run `python scripts/build_bbp.py --test`. This requires GNU make and a C++20 g++. The script stages the binary and license notices in `src/gambitpairing/resources/bin/` for packaging. Build outputs are git-ignored.

Build on each target platform before packaging. Wheels get a platform-specific tag, and PyInstaller bundles the engine with its notices. Source archives include the vendored source and build script, but no platform binary. Wheel builds from source compile BBP if it has not been staged yet.

## Runtime

BBP runs as a subprocess, not a Python extension. The GUI, generator, comparisons and benchmarks all find the bundled binary automatically. An explicit path or environment override exists for testing other versions. No runtime downloads or compilation occur, and the native GP engine never calls BBP.
