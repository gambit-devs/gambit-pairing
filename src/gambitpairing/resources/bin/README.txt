Integrated BBP Pairings runtime

Build the pinned C++ source in vendor/bbp with:
    python scripts/build_bbp.py --test
On Kinoite, run that command in the existing Fedora Toolbox.

The build stages bbpPairings.exe and upstream license notices here. The GUI and
all CLI pairing commands discover it automatically. Despite the .exe suffix,
upstream uses this filename on Linux too. Binaries are platform-specific build
outputs, not tracked source. See vendor/README.md for provenance and licensing.
