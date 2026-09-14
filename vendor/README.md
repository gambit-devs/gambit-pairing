# Third-party engines

`bbp/` contains the unmodified upstream BBP Pairings **v6.0.0** source,
including its Apache-2.0 license and regression tests.

- Upstream: https://github.com/BieremaBoyzProgramming/bbpPairings/tree/v6.0.0
- Archive: https://codeload.github.com/BieremaBoyzProgramming/bbpPairings/tar.gz/refs/tags/v6.0.0
- Archive SHA-256: `b7f95c0803131e38a56e8829bd062d9ad51908322dd6fef01380b2f612f58227`
- Dutch engine: `bbp/src/swisssystems/dutch.cpp`
- Matching implementation: `bbp/src/matching/`
- Program entry point: `bbp/src/main.cpp`

From the project root, run `python scripts/build_bbp.py --test` with GNU make
and a C++20-capable g++ installed. On Kinoite use the existing Toolbox, e.g.
`toolbox run -c fedora-toolbox-44 python3 scripts/build_bbp.py --test`.
Build before making application distributions; the script stages the binary
and license notices in `src/gambitpairing/resources/bin/` for package inclusion.
Build outputs are ignored, source and upstream tests are tracked.

Build separately on each target platform before packaging. Wheels containing
the staged engine receive a platform-specific tag (not `py3-none-any`);
PyInstaller includes both the engine and its license notices. Source archives
include this vendored C++ source and the build script, but not a platform binary.
Wheel builds from source compile BBP if it has not been staged yet, so they need
make and g++. For source development, stage it once before installing the app;
no runtime downloads or compilation occur.

BBP remains a subprocess engine, not a Python extension. GUI, generator,
comparisons and benchmarks discover the same bundled binary automatically.
An explicit path/environment override remains available for testing another
version, but ordinary runs do not require executable arguments. The native GP
engine remains independent and never calls BBP to complete its search.
