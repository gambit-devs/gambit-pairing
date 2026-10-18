"""Parsers for downloaded FIDE and CFC player lists.

Both parsers stream rows so a full FIDE list (close to two million players)
never has to sit in memory at once. Each parser fills a :class:`ParseReport`
with the number of rows read and the number skipped, by reason.
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

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
import xml.etree.ElementTree as ET
import zipfile

from gambitpairing.player_lists.catalog import (
    RATING_BLITZ,
    RATING_RAPID,
    RATING_STANDARD,
)

# Skip reasons reported by the parsers.
SKIP_BAD_ID = "missing or invalid ID"
SKIP_NO_NAME = "no name"
SKIP_ANONYMOUS = "anonymous member"
SKIP_DUPLICATE_ID = "duplicate ID"
SKIP_TOO_FEW_FIELDS = "too few fields"
SKIP_BAD_NUMBER = "unreadable number"

# Values the CFC list uses in place of a real value.
CFC_PLACEHOLDERS = frozenset({"", "-", "--", "---", ".", "?", "x"})
CFC_ANONYMOUS = "anonymous"

# CFC header titles mapped to the keys the parser yields.
CFC_HEADER_KEYS: dict[str, str] = {
    "cfc#": "cfc_id",
    "expiry": "expiry",
    "last": "last",
    "first": "first",
    "prov": "province",
    "city": "city",
    "rating": "rating",
    "high": "high",
    "active rtg": "active_rating",
    "active high": "active_high",
    "fide number": "fide_id",
    "fide rating": "fide_rating",
}
CFC_REQUIRED_KEYS = ("cfc_id", "last", "first")
CFC_INTEGER_KEYS = (
    "rating",
    "high",
    "active_rating",
    "active_high",
    "fide_id",
    "fide_rating",
)
# The only CFC column whose values contain commas ("Marseille, FRANCE").
CFC_FREE_TEXT_KEY = "city"

FIDE_RATING_ELEMENTS: dict[str, str] = {
    RATING_STANDARD: "rating",
    RATING_RAPID: "rapid_rating",
    RATING_BLITZ: "blitz_rating",
}


class PlayerListFormatError(ValueError):
    """Raised when a file is not the player list it claims to be."""


@dataclass
class ParseReport:
    """Rows read from a player list and rows skipped, by reason."""

    rows: int = 0
    skipped: Counter = field(default_factory=Counter)

    @property
    def skipped_total(self) -> int:
        return sum(self.skipped.values())

    def skip(self, reason: str) -> None:
        self.skipped[reason] += 1

    def summary(self) -> str:
        """Return text such as ``"78,382 rows read, 56 skipped (42 anonymous member, …)"``."""
        text = f"{self.rows:,} rows read"
        if not self.skipped:
            return text
        reasons = ", ".join(
            f"{count:,} {reason}" for reason, count in self.skipped.most_common()
        )
        return f"{text}, {self.skipped_total:,} skipped ({reasons})"


# --- FIDE --------------------------------------------------------------------


def fide_xml_member_name(archive: zipfile.ZipFile) -> str:
    """Return the name of the XML member inside a FIDE list archive.

    FIDE renames the member from time to time (the combined list currently
    holds ``players_list_xml_foa.xml``), so the name is read from the archive.
    """
    members = [
        info
        for info in archive.infolist()
        if not info.is_dir() and info.filename.lower().endswith(".xml")
    ]
    if not members:
        raise PlayerListFormatError("The archive does not contain an XML file")
    return max(members, key=lambda info: info.file_size).filename


def iter_fide_players(
    path: Path | str, report: ParseReport, rating_kind: Optional[str] = None
) -> Iterator[dict[str, Any]]:
    """Yield players from a FIDE XML zip file.

    ``rating_kind`` names the rating held by ``<rating>`` in single-type lists
    (standard, rapid or blitz). Combined lists carry ``<rating>``,
    ``<rapid_rating>`` and ``<blitz_rating>`` and are read with ``None``.
    """
    seen: set[int] = set()
    with zipfile.ZipFile(path) as archive:
        member = fide_xml_member_name(archive)
        with archive.open(member) as stream:
            found_root = False
            try:
                for _event, element in ET.iterparse(stream, events=("end",)):
                    if element.tag != "player":
                        continue
                    found_root = True
                    player = _fide_player_from_element(element, rating_kind)
                    element.clear()
                    reason = _fide_skip_reason(player, seen)
                    if reason:
                        report.skip(reason)
                        continue
                    seen.add(player["fide_id"])
                    report.rows += 1
                    yield player
            except ET.ParseError as error:
                raise PlayerListFormatError(f"Invalid FIDE XML: {error}") from error
            if not found_root:
                raise PlayerListFormatError("The FIDE XML file has no <player> rows")


def _fide_player_from_element(
    element: ET.Element, rating_kind: Optional[str]
) -> dict[str, Any]:
    def text(tag: str) -> str:
        return (element.findtext(tag) or "").strip()

    ratings: dict[str, Optional[int]] = {}
    for kind, tag in FIDE_RATING_ELEMENTS.items():
        source_tag = "rating" if rating_kind == kind else tag
        if rating_kind is not None and rating_kind != kind:
            ratings[kind] = None
        else:
            ratings[kind] = _positive_int(text(source_tag))

    flag = text("flag").lower()
    return {
        "fide_id": _positive_int(text("fideid")),
        "name": text("name"),
        "federation": text("country"),
        "sex": text("sex").upper()[:1],
        "title": text("title") or text("w_title"),
        "standard": ratings[RATING_STANDARD],
        "rapid": ratings[RATING_RAPID],
        "blitz": ratings[RATING_BLITZ],
        "birth_year": _positive_int(text("birthday")),
        "inactive": "i" in flag,
    }


def _fide_skip_reason(player: dict[str, Any], seen: set[int]) -> Optional[str]:
    if player["fide_id"] is None:
        return SKIP_BAD_ID
    if not player["name"]:
        return SKIP_NO_NAME
    if player["fide_id"] in seen:
        return SKIP_DUPLICATE_ID
    return None


# --- CFC ---------------------------------------------------------------------


def decode_cfc_text(data: bytes) -> str:
    """Decode the CFC list, which is published in Windows-1252, not UTF-8."""
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def iter_cfc_members(path: Path | str, report: ParseReport) -> Iterator[dict[str, Any]]:
    """Yield members from a CFC ``tdlist.txt`` file."""
    yield from iter_cfc_members_from_text(
        decode_cfc_text(Path(path).read_bytes()), report
    )


def iter_cfc_members_from_text(
    text: str, report: ParseReport
) -> Iterator[dict[str, Any]]:
    """Yield members from the text of a CFC ``tdlist.txt`` file.

    The file is comma-separated with quoted fields, but the quoting is not
    reliable: the City field usually lacks its opening quote, an empty city is
    written as a lone ``"``, and cities such as ``Marseille, FRANCE`` add an
    extra comma. Fields are therefore split on commas, quotes are stripped
    from each field, and any extra fields are folded back into City. Rows
    whose numbers still do not line up are skipped and counted.
    """
    lines = text.splitlines()
    if not lines:
        raise PlayerListFormatError("The CFC list is empty")

    header = [_cfc_clean(title).lower() for title in lines[0].split(",")]
    keys = [CFC_HEADER_KEYS.get(title, "") for title in header]
    missing = [key for key in CFC_REQUIRED_KEYS if key not in keys]
    if missing:
        raise PlayerListFormatError(
            "The CFC list header is missing " + ", ".join(missing)
        )
    free_index = keys.index(CFC_FREE_TEXT_KEY) if CFC_FREE_TEXT_KEY in keys else -1

    seen: set[int] = set()
    for line in lines[1:]:
        if not line.strip():
            continue
        fields = _cfc_fields(line, len(keys), free_index)
        if fields is None:
            report.skip(SKIP_TOO_FEW_FIELDS)
            continue
        values = {key: _cfc_clean(value) for key, value in zip(keys, fields) if key}
        member, reason = _cfc_member_from_values(values)
        if reason is None and member["cfc_id"] in seen:
            reason = SKIP_DUPLICATE_ID
        if reason:
            report.skip(reason)
            continue
        seen.add(member["cfc_id"])
        report.rows += 1
        yield member


def _cfc_fields(line: str, width: int, free_index: int) -> Optional[list[str]]:
    fields = line.split(",")
    if len(fields) < width:
        return None
    if len(fields) == width or free_index < 0:
        return fields[:width]
    tail = width - free_index - 1
    end = len(fields) - tail
    return fields[:free_index] + [",".join(fields[free_index:end])] + fields[end:]


def _cfc_clean(value: str) -> str:
    cleaned = value.strip().strip('"').strip()
    return "" if cleaned in CFC_PLACEHOLDERS else cleaned


def _cfc_member_from_values(
    values: dict[str, str],
) -> tuple[dict[str, Any], Optional[str]]:
    cfc_id = _positive_int(values.get("cfc_id", ""))
    if cfc_id is None:
        return {}, SKIP_BAD_ID

    first = values.get("first", "")
    last = values.get("last", "")
    if CFC_ANONYMOUS in (first.lower(), last.lower()):
        return {}, SKIP_ANONYMOUS
    if not first and not last:
        return {}, SKIP_NO_NAME

    member: dict[str, Any] = {
        "cfc_id": cfc_id,
        "first": first,
        "last": last,
        "expiry": values.get("expiry", ""),
        "province": values.get("province", ""),
        "city": values.get("city", ""),
    }
    for key in CFC_INTEGER_KEYS:
        raw = values.get(key, "")
        # Some rows hold -1 in the High columns; that is a number, not junk.
        if raw and not raw.lstrip("-").isdigit():
            return {}, SKIP_BAD_NUMBER
        member[key] = _positive_int(raw)
    return member, None


def _positive_int(value: str) -> Optional[int]:
    """Return ``value`` as a positive integer, or ``None`` for 0 and junk."""
    value = value.strip()
    if not value.isdigit():
        return None
    number = int(value)
    return number if number > 0 else None
