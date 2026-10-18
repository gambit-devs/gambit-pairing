"""Search FIDE and CFC players and merge the results into one table.

Each source is searched on its own (so the dialog can show per-source
progress) from the downloaded list when there is one, and from the live FIDE
and CFC lookups otherwise. The results are merged on FIDE number: CFC records
carry a FIDE Number field, so a CFC member whose FIDE number matches a FIDE
result shares that row.
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

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
import sqlite3
from typing import Any, Optional

from gambitpairing.player_lists.catalog import (
    RATING_BLITZ,
    RATING_RAPID,
    RATING_STANDARD,
    SOURCE_CFC,
    SOURCE_FIDE,
    PlayerListSpec,
)
from gambitpairing.player_lists.store import (
    CFC_TABLE,
    FIDE_TABLE,
    PlayerListStore,
    name_key,
)
from gambitpairing.utils.api_adapters import (
    cfc_api_to_player_dict,
    cfc_api_to_search_result,
    fide_api_to_player_dict,
)

SEARCH_SOURCES: tuple[str, ...] = (SOURCE_FIDE, SOURCE_CFC)
MIN_NAME_LENGTH = 2
RESULT_LIMIT = 100

ORIGIN_LOCAL = "local list"
ORIGIN_LIVE = "online"

SOURCE_LABEL_BOTH = f"{SOURCE_FIDE} + {SOURCE_CFC}"


class SearchMode(Enum):
    NAME = "Name"
    FIDE_ID = "FIDE ID"
    CFC_ID = "CFC ID"


SEARCH_MODES: tuple[SearchMode, ...] = tuple(SearchMode)


def selected_sources(fide_checked: bool, cfc_checked: bool) -> tuple[str, ...]:
    """Return the sources to search for the state of the source checkboxes."""
    checked = {SOURCE_FIDE: fide_checked, SOURCE_CFC: cfc_checked}
    return tuple(source for source in SEARCH_SOURCES if checked[source])


@dataclass(frozen=True)
class SearchRequest:
    mode: SearchMode
    term: str
    sources: tuple[str, ...]

    @classmethod
    def from_inputs(
        cls, mode: SearchMode, term: str, fide_checked: bool, cfc_checked: bool
    ) -> "SearchRequest":
        return cls(mode, term.strip(), selected_sources(fide_checked, cfc_checked))

    @property
    def player_id(self) -> Optional[int]:
        """The ID searched for, for ID modes with a valid positive number."""
        if self.mode is SearchMode.NAME or not self.term.isdigit():
            return None
        number = int(self.term)
        return number if number > 0 else None

    def validation_error(self) -> Optional[str]:
        """Return why the request cannot run, or None when it can."""
        if not self.sources:
            return "Choose at least one source (FIDE or CFC) to search."
        if not self.term:
            noun = "name" if self.mode is SearchMode.NAME else self.mode.value
            return f"Enter a {noun} to search for."
        if self.mode is SearchMode.NAME:
            if len(self.term) < MIN_NAME_LENGTH:
                return f"Enter at least {MIN_NAME_LENGTH} characters for a name search."
            return None
        if self.player_id is None:
            return f"A {self.mode.value} is a positive whole number, such as 1503014."
        return None


# --- normalized hits -----------------------------------------------------------


@dataclass(frozen=True)
class PlayerSearchHit:
    """One player from one source, in the shape the results table needs.

    ``record`` keeps the source's own record, in the shape the existing
    adapters (``fide_api_to_player_dict`` and ``cfc_api_to_player_dict``)
    accept, so filling the form keeps each source's behaviour.
    """

    source: str
    name: str
    fide_id: Optional[int] = None
    cfc_id: Optional[int] = None
    fide_standard: Optional[int] = None
    fide_rapid: Optional[int] = None
    fide_blitz: Optional[int] = None
    cfc_rating: Optional[int] = None
    cfc_active_rating: Optional[int] = None
    record: Mapping[str, Any] = field(default_factory=dict, compare=False)


def _optional_int(value: Any) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if not text.isdigit():
        return None
    number = int(text)
    return number if number > 0 else None


def fide_hit(record: Mapping[str, Any]) -> PlayerSearchHit:
    """Normalize a FIDE record (live search, live profile or local list)."""
    return PlayerSearchHit(
        source=SOURCE_FIDE,
        name=str(record.get("name") or "").strip(),
        fide_id=_optional_int(record.get("fide_id")),
        fide_standard=_optional_int(record.get("standard_rating")),
        fide_rapid=_optional_int(record.get("rapid_rating")),
        fide_blitz=_optional_int(record.get("blitz_rating")),
        record=dict(record),
    )


def cfc_hit(record: Mapping[str, Any]) -> PlayerSearchHit:
    """Normalize a CFC record (live API, live search page or local list)."""
    display = cfc_api_to_search_result(dict(record))
    return PlayerSearchHit(
        source=SOURCE_CFC,
        name=str(display["name"]),
        fide_id=_optional_int(record.get("fide_id")),
        cfc_id=_optional_int(record.get("cfc_id")),
        cfc_rating=_optional_int(record.get("rating") or record.get("regular_rating")),
        cfc_active_rating=_optional_int(record.get("quick_rating")),
        record=dict(record),
    )


# --- merging -------------------------------------------------------------------


def _rating_text(primary: Optional[int], *fallbacks: tuple[Optional[int], str]) -> str:
    if primary:
        return str(primary)
    for rating, label in fallbacks:
        if rating:
            return f"{rating} ({label})"
    return ""


@dataclass(frozen=True)
class MergedSearchRow:
    """One row of the merged results table."""

    fide: Optional[PlayerSearchHit] = None
    cfc: Optional[PlayerSearchHit] = None

    @property
    def name(self) -> str:
        return (self.fide.name if self.fide else "") or (
            self.cfc.name if self.cfc else ""
        )

    @property
    def source_label(self) -> str:
        if self.fide and self.cfc:
            return SOURCE_LABEL_BOTH
        return SOURCE_FIDE if self.fide else SOURCE_CFC

    @property
    def fide_id(self) -> Optional[int]:
        if self.fide and self.fide.fide_id:
            return self.fide.fide_id
        return self.cfc.fide_id if self.cfc else None

    @property
    def cfc_id(self) -> Optional[int]:
        return self.cfc.cfc_id if self.cfc else None

    @property
    def fide_rating_text(self) -> str:
        """The FIDE standard rating, or rapid/blitz labelled as such."""
        if not self.fide:
            return ""
        return _rating_text(
            self.fide.fide_standard,
            (self.fide.fide_rapid, "rapid"),
            (self.fide.fide_blitz, "blitz"),
        )

    @property
    def cfc_rating_text(self) -> str:
        """The CFC regular rating, or the active rating labelled as such."""
        if not self.cfc:
            return ""
        return _rating_text(self.cfc.cfc_rating, (self.cfc.cfc_active_rating, "active"))

    def player_data(self) -> dict[str, Any]:
        """Return the standardized player dict for the details form.

        A FIDE-only or CFC-only row uses that source's adapter unchanged. A
        merged row starts from the CFC data and lets every non-empty FIDE
        value win, so it keeps both IDs, the FIDE fields and the CFC location.
        """
        data: dict[str, Any] = {}
        if self.cfc:
            data.update(cfc_api_to_player_dict(dict(self.cfc.record)))
        if self.fide:
            fide_data = fide_api_to_player_dict(dict(self.fide.record))
            data.update(
                {
                    key: value
                    for key, value in fide_data.items()
                    if value not in (None, "")
                }
            )
        return data


def name_rank(name: str, term: str) -> int:
    """Rank how well ``name`` matches a name search (lower is better).

    0: the name starts with the first search word (FIDE and the CFC list put
    the surname first); 1: that whole word appears; 2: only a prefix matches.
    """
    words = name_key(term).split()
    if not words:
        return 0
    key = name_key(name)
    if key == f" {words[0]}" or key.startswith(f" {words[0]} "):
        return 0
    return 1 if f" {words[0]} " in key + " " else 2


def merge_search_hits(
    fide_hits: Sequence[PlayerSearchHit],
    cfc_hits: Sequence[PlayerSearchHit],
    term: str = "",
) -> list[MergedSearchRow]:
    """Merge results from both sources into table rows.

    Rows merge on FIDE number. Duplicate FIDE IDs and duplicate CFC IDs are
    dropped. A CFC member without a FIDE number, or whose FIDE number matches
    no FIDE result (or one already claimed by another CFC member), keeps a
    row of its own. Rows are sorted by how well the name matches ``term``
    (see :func:`name_rank`), then by name.
    """
    fide_by_id: dict[int, PlayerSearchHit] = {}
    fide_without_id: list[PlayerSearchHit] = []
    for hit in fide_hits:
        if hit.fide_id is None:
            fide_without_id.append(hit)
        elif hit.fide_id not in fide_by_id:
            fide_by_id[hit.fide_id] = hit

    paired: dict[int, PlayerSearchHit] = {}
    cfc_only: list[PlayerSearchHit] = []
    seen_cfc: set[int] = set()
    for hit in cfc_hits:
        if hit.cfc_id is not None:
            if hit.cfc_id in seen_cfc:
                continue
            seen_cfc.add(hit.cfc_id)
        if hit.fide_id in fide_by_id and hit.fide_id not in paired:
            paired[hit.fide_id] = hit
        else:
            cfc_only.append(hit)

    rows = [
        MergedSearchRow(fide=hit, cfc=paired.get(fide_id))
        for fide_id, hit in fide_by_id.items()
    ]
    rows.extend(MergedSearchRow(fide=hit) for hit in fide_without_id)
    rows.extend(MergedSearchRow(cfc=hit) for hit in cfc_only)
    return sorted(rows, key=lambda row: (name_rank(row.name, term), name_key(row.name)))


# --- per-source status -----------------------------------------------------------


class SourceState(Enum):
    SEARCHING = "searching"
    DONE = "done"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class SourceStatus:
    source: str
    state: SourceState
    count: int = 0
    origin: str = ""
    message: str = ""
    truncated: bool = False

    def text(self) -> str:
        if self.state is SourceState.SEARCHING:
            return f"{self.source}: searching…"
        if self.state is SourceState.FAILED:
            return f"{self.source}: error: {self.message}"
        if self.state is SourceState.UNAVAILABLE:
            return f"{self.source}: {self.message}"
        noun = "result" if self.count == 1 else "results"
        count = f"{self.count}+" if self.truncated else str(self.count)
        origin = f" ({self.origin})" if self.origin else ""
        note = f"; {self.message}" if self.message else ""
        return f"{self.source}: {count} {noun}{origin}{note}"


def format_search_status(statuses: Sequence[SourceStatus]) -> str:
    """Return the status line, e.g. ``"FIDE: 20 results · CFC: searching…"``."""
    return " · ".join(status.text() for status in statuses)


# --- searching -----------------------------------------------------------------


def _live_cfc_by_id(cfc_id: int) -> Optional[dict]:
    from gambitpairing.utils.api import get_cfc_player_info

    return get_cfc_player_info(str(cfc_id))


@dataclass(frozen=True)
class LiveLookups:
    """Online lookups for CFC ID searches when no CFC list is downloaded."""

    cfc_by_id: Callable[[int], Optional[dict]] = _live_cfc_by_id


@dataclass(frozen=True)
class SourceResult:
    source: str
    hits: tuple[PlayerSearchHit, ...]
    origin: str
    message: str = ""
    available: bool = True

    def status(self) -> SourceStatus:
        if not self.available:
            return SourceStatus(
                self.source, SourceState.UNAVAILABLE, message=self.message
            )
        return SourceStatus(
            self.source,
            SourceState.DONE,
            count=len(self.hits),
            origin=self.origin,
            message=self.message,
            truncated=len(self.hits) >= RESULT_LIMIT,
        )


def search_source(
    source: str,
    request: SearchRequest,
    store: PlayerListStore,
    live: Optional[LiveLookups] = None,
) -> SourceResult:
    """Search one source's downloaded list, with live CFC ID lookups as a fallback."""
    live = live or LiveLookups()
    if source == SOURCE_FIDE:
        return _search_fide(request, store, live)
    if source == SOURCE_CFC:
        return _search_cfc(request, store, live)
    raise ValueError(f"Unknown search source {source!r}")


def _search_fide(
    request: SearchRequest, store: PlayerListStore, live: LiveLookups
) -> SourceResult:
    specs = _preferred_fide_specs(store)
    if not specs:
        return SourceResult(
            SOURCE_FIDE,
            (),
            ORIGIN_LOCAL,
            message="needs the FIDE list (Player lists…)",
            available=False,
        )

    if request.mode is SearchMode.NAME:
        records = _local_fide_records(store, specs, name=request.term)
        return SourceResult(SOURCE_FIDE, _hits(fide_hit, records), ORIGIN_LOCAL)

    fide_id = request.player_id
    message = ""
    if request.mode is SearchMode.CFC_ID:
        # FIDE has no CFC IDs; follow the CFC record's FIDE number.
        fide_id = _fide_number_for_cfc_id(store, live, request.player_id)
        if fide_id is None:
            return SourceResult(
                SOURCE_FIDE,
                (),
                ORIGIN_LOCAL,
                message="that CFC member has no FIDE number",
            )
        message = f"via FIDE number {fide_id}"

    records = _local_fide_records(store, specs, fide_id=fide_id)
    return SourceResult(SOURCE_FIDE, _hits(fide_hit, records), ORIGIN_LOCAL, message)


def _search_cfc(
    request: SearchRequest, store: PlayerListStore, live: LiveLookups
) -> SourceResult:
    specs = store.downloaded_specs(SOURCE_CFC)
    if specs:
        records = _local_cfc_records(store, specs[0], request)
        return SourceResult(SOURCE_CFC, _hits(cfc_hit, records), ORIGIN_LOCAL)

    if request.mode is SearchMode.CFC_ID:
        record = live.cfc_by_id(request.player_id or 0)
        records = [record] if record else []
        return SourceResult(SOURCE_CFC, _hits(cfc_hit, records), ORIGIN_LIVE)

    return SourceResult(
        SOURCE_CFC,
        (),
        ORIGIN_LOCAL,
        message="needs the CFC member list (Player lists…)",
        available=False,
    )


def _hits(
    normalize: Callable[[Mapping[str, Any]], PlayerSearchHit], records: Any
) -> tuple[PlayerSearchHit, ...]:
    if isinstance(records, Mapping):
        records = [records]
    return tuple(
        normalize(record)
        for record in list(records or [])[:RESULT_LIMIT]
        if isinstance(record, Mapping)
    )


def _fide_number_for_cfc_id(
    store: PlayerListStore, live: LiveLookups, cfc_id: Optional[int]
) -> Optional[int]:
    if cfc_id is None:
        return None
    specs = store.downloaded_specs(SOURCE_CFC)
    if specs:
        request = SearchRequest(SearchMode.CFC_ID, str(cfc_id), (SOURCE_CFC,))
        records = _local_cfc_records(store, specs[0], request)
    else:
        record = live.cfc_by_id(cfc_id)
        records = [record] if record else []
    for record in records:
        fide_id = _optional_int(record.get("fide_id"))
        if fide_id:
            return fide_id
    return None


def _preferred_fide_specs(store: PlayerListStore) -> tuple[PlayerListSpec, ...]:
    """Use the combined list when downloaded, else whichever single lists are."""
    specs = store.downloaded_specs(SOURCE_FIDE)
    combined = [spec for spec in specs if spec.rating_kind is None]
    return tuple(combined[:1]) if combined else specs


def _name_query(term: str) -> tuple[str, list[Any]]:
    """Return ``WHERE … ORDER BY …`` SQL for a name search, with its parameters.

    Every word of ``term`` must start a word of the name. Names whose surname
    (the first word of the key) is the first search word come first, then
    names with that whole word anywhere, then prefix matches; ties sort by
    name.
    """
    words = name_key(term).split()
    where = " AND ".join("name_key LIKE ?" for _ in words) or "0"
    order = (
        "CASE WHEN name_key = ? OR name_key LIKE ? THEN 0 "
        "WHEN name_key || ' ' LIKE ? THEN 1 ELSE 2 END, name_key"
    )
    first = words[0] if words else ""
    params: list[Any] = [f"% {word}%" for word in words]
    params += [f" {first}", f" {first} %", f"% {first} %"]
    return f"{where} ORDER BY {order}", params


def _local_fide_records(
    store: PlayerListStore,
    specs: Sequence[PlayerListSpec],
    name: str = "",
    fide_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Look players up in the downloaded FIDE lists.

    When several single-type lists are downloaded, a player's ratings are
    gathered from each of them.
    """
    if fide_id is not None:
        where, params = "fide_id = ?", [fide_id]
    else:
        where, params = _name_query(name)
    query = f"SELECT * FROM {FIDE_TABLE} WHERE {where} LIMIT {RESULT_LIMIT}"

    merged: dict[int, dict[str, Any]] = {}
    for spec in specs:
        with store.connect(spec) as connection:
            for row in connection.execute(query, params):
                record = merged.setdefault(row["fide_id"], _fide_record(row))
                for kind, key in (
                    (RATING_STANDARD, "standard_rating"),
                    (RATING_RAPID, "rapid_rating"),
                    (RATING_BLITZ, "blitz_rating"),
                ):
                    if row[kind] and not record.get(key):
                        record[key] = row[kind]
    return list(merged.values())


def _fide_record(row: sqlite3.Row) -> dict[str, Any]:
    """Build the FIDE record shape that the search adapters expect."""
    return {
        "fide_id": str(row["fide_id"]),
        "name": row["name"],
        "title": row["title"] or None,
        "federation": row["federation"] or None,
        "standard_rating": row["standard"],
        "rapid_rating": row["rapid"],
        "blitz_rating": row["blitz"],
        "birth_year": row["birth_year"],
        "gender": row["sex"] if row["sex"] in ("M", "F") else None,
        "active": not row["inactive"],
    }


def _local_cfc_records(
    store: PlayerListStore, spec: PlayerListSpec, request: SearchRequest
) -> list[dict[str, Any]]:
    if request.mode is SearchMode.NAME:
        where, params = _name_query(request.term)
    elif request.mode is SearchMode.FIDE_ID:
        where, params = "fide_id = ?", [request.player_id]
    else:
        where, params = "cfc_id = ?", [request.player_id]
    query = f"SELECT * FROM {CFC_TABLE} WHERE {where} LIMIT {RESULT_LIMIT}"
    with store.connect(spec) as connection:
        return [_cfc_record(row) for row in connection.execute(query, params)]


def _cfc_record(row: sqlite3.Row) -> dict[str, Any]:
    """Build the record shape the CFC player API returns."""
    first, last = row["first"] or "", row["last"] or ""
    record: dict[str, Any] = {
        "cfc_id": row["cfc_id"],
        "name": f"{last}, {first}" if first and last else (last or first),
        "name_first": first,
        "name_last": last,
        "regular_rating": row["rating"] or 0,
        "quick_rating": row["active_rating"] or 0,
        "addr_city": row["city"] or "",
        "addr_province": row["province"] or "",
        "cfc_expiry": row["expiry"] or "",
    }
    if row["fide_id"]:
        record["fide_id"] = row["fide_id"]
    return record
