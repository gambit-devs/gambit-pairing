#!/usr/bin/env python3
"""Redraw the version in the README's ASCII banner.

The version is drawn in pyfiglet's "standard" font at column 20 of the banner.
Underscore bars at columns 0 and 34, on the third and fourth rows, frame it.
The banner shows major.minor, so 0.8.0 is drawn as 0.8.

Usage:
  python scripts/update_readme_version.py 0.9
  python scripts/update_readme_version.py 0.9.0 --dry-run

Needs pyfiglet (pip install pyfiglet). Only the banner's five rows change; the
rest of the README is written back as it was, including its line endings.
"""

import argparse
from functools import lru_cache
from pathlib import Path
import re
import sys

try:
    import pyfiglet
except ImportError:  # Reported in main() with the install command.
    pyfiglet = None

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"

FONT = "standard"
VERSION_COLUMN = 20
BAR_COLUMNS = (0, 34)
BAR_ROWS = (2, 3)
BANNER_HEIGHT = 5
VERSION_PATTERN = re.compile(r"v?(\d+)\.(\d+)(?:\.\d+)?")


class BannerError(Exception):
    """The banner could not be drawn or found."""


def _figlet_rows(text: str) -> list[str]:
    if pyfiglet is None:
        raise BannerError("pyfiglet is not installed. Run: pip install pyfiglet")
    rows = [row.rstrip() for row in pyfiglet.figlet_format(text, font=FONT).split("\n")]
    while rows and not rows[-1]:
        rows.pop()
    return rows


def version_rows(version: str) -> list[str]:
    """Return the banner rows for a version, without blank rows around it."""
    rows = _figlet_rows(version)
    while rows and not rows[0]:
        rows.pop(0)
    if len(rows) != BANNER_HEIGHT:
        raise BannerError(f"{version!r} does not draw as {BANNER_HEIGHT} rows")
    return rows


@lru_cache(maxsize=1)
def bar_rows() -> tuple[str, str]:
    """Return the two rows of the underscore bar that frames the version."""
    rows = [row for row in _figlet_rows("___") if row.strip()]
    if len(rows) != 2:
        raise BannerError("The underscore bar does not draw as two rows")
    return rows[0], rows[1]


def compose(version: str) -> list[str]:
    """Return the five banner rows for a version, without trailing spaces."""
    art = version_rows(version)
    bar_top, bar_bottom = bar_rows()
    bar = {BAR_ROWS[0]: bar_top, BAR_ROWS[1]: bar_bottom}
    width = max(
        max(BAR_COLUMNS) + max(len(bar_top), len(bar_bottom)),
        VERSION_COLUMN + max(len(row) for row in art),
    )
    canvas = [[" "] * width for _ in range(BANNER_HEIGHT)]

    def place(row_index: int, column: int, text: str) -> None:
        for offset, char in enumerate(text):
            if char == " ":
                continue
            cell = column + offset
            if canvas[row_index][cell] != " ":
                raise BannerError(
                    f"{version!r} is too wide: it runs into the banner's bar. "
                    "Use a shorter version."
                )
            canvas[row_index][cell] = char

    for row_index, text in enumerate(art):
        place(row_index, VERSION_COLUMN, text)
    for row_index, text in bar.items():
        for column in BAR_COLUMNS:
            place(row_index, column, text)
    return ["".join(row).rstrip() for row in canvas]


def find_banner(lines: list[str]) -> int:
    """Return the index of the banner's first row, found from its bars."""
    bar_top, bar_bottom = bar_rows()
    found = []
    for row in range(len(lines) - 1):
        if all(
            lines[row][column : column + len(bar_top)].rstrip() == bar_top.rstrip()
            and lines[row + 1][column : column + len(bar_bottom)].rstrip()
            == bar_bottom.rstrip()
            for column in BAR_COLUMNS
        ):
            start = row - BAR_ROWS[0]
            if start >= 0 and start + BANNER_HEIGHT <= len(lines):
                found.append(start)
    if not found:
        raise BannerError("The version banner was not found in the README")
    if len(found) > 1:
        raise BannerError("More than one version banner was found in the README")
    start = found[0]
    rows = lines[start : start + BANNER_HEIGHT]
    for index in (0, 1, BANNER_HEIGHT - 1):
        if rows[index][:VERSION_COLUMN].strip():
            raise BannerError(
                "The banner has unexpected text to the left of the version"
            )
    return start


def update_readme(text: str, version: str) -> tuple[str, bool]:
    """Return the README text with its banner redrawn, and whether it changed."""
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.replace("\r\n", "\n").split("\n")
    start = find_banner(lines)
    current = [line.rstrip() for line in lines[start : start + BANNER_HEIGHT]]
    replacement = compose(version)
    lines[start : start + BANNER_HEIGHT] = replacement
    return newline.join(lines), current != replacement


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("version", help="Version to draw, such as 0.9 or 0.9.0")
    parser.add_argument("--readme", type=Path, default=README, help="README to edit")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the banner rows for the version and leave the README alone",
    )
    args = parser.parse_args(argv)

    match = VERSION_PATTERN.fullmatch(args.version.strip())
    if match is None:
        print(f"[x] Expected a version like 0.9 or 0.9.0, got {args.version!r}")
        return 1
    shown = f"{match.group(1)}.{match.group(2)}"

    try:
        if args.dry_run:
            print("\n".join(compose(shown)))
            return 0
        with open(args.readme, encoding="utf-8", newline="") as handle:
            text = handle.read()
        updated, changed = update_readme(text, shown)
    except BannerError as error:
        print(f"[x] {error}", file=sys.stderr)
        return 1

    if not changed:
        print(f"The banner already shows {shown}; nothing to change.")
        return 0
    with open(args.readme, "w", encoding="utf-8", newline="") as handle:
        handle.write(updated)
    print(f"The banner in {args.readme} now shows {shown}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
