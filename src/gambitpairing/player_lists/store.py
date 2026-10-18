"""Local storage for downloaded player lists.

Each list lives in its own folder under the app's data directory::

    <data dir>/player_lists/<key>/<file name>      the file as downloaded
    <data dir>/player_lists/<key>/index.sqlite3    search index built from it
    <data dir>/player_lists/<key>/metadata.json    source headers and counts

New downloads are written to temporary files in the same folder, validated,
and only then moved over the old copy with ``os.replace``.
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

from collections.abc import Callable, Iterable, Iterator
import contextlib
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import tempfile
from typing import Any, Optional
import unicodedata
import zipfile

from gambitpairing.constants import (
    DEFAULT_PLAYER_LISTS,
    PLAYER_LIST_CHECK_INTERVAL_SECONDS,
    PLAYER_LIST_MAX_ROW_DROP,
    PLAYER_LIST_MIN_ROWS,
)
from gambitpairing.player_lists.catalog import (
    FORMAT_CFC_TDLIST,
    FORMAT_FIDE_XML_ZIP,
    PLAYER_LISTS,
    PLAYER_LISTS_BY_KEY,
    PlayerListSpec,
)
from gambitpairing.player_lists.parsers import (
    ParseReport,
    iter_cfc_members,
    iter_fide_players,
)
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)

# Bump when the index tables or metadata fields change; older copies are
# then re-indexed from the stored file.
PLAYER_LIST_SCHEMA_VERSION = 1

DATA_DIR_ENV = "GAMBIT_PAIRING_DATA_DIR"
PLAYER_LISTS_DIR_NAME = "player_lists"
SELECTION_FILE_NAME = "selection.json"
METADATA_FILE_NAME = "metadata.json"
INDEX_FILE_NAME = "index.sqlite3"
TEMP_SUFFIX = ".part"
# Temporary files older than this are left over from an interrupted run.
STALE_TEMP_SECONDS = 60 * 60
INDEX_BATCH_SIZE = 5000

_NAME_KEY_STRIP = re.compile(r"[^0-9a-z]+")
_MD5_ETAG = re.compile(r'^(?:W/)?"?([0-9a-fA-F]{32})"?$')


class PlayerListValidationError(Exception):
    """Raised when a downloaded list fails validation; the old copy is kept."""


class OperationCancelled(Exception):
    """Raised when the caller cancels a download or an index build."""


class ListState(Enum):
    NOT_DOWNLOADED = "not downloaded"
    DOWNLOADED = "downloaded"
    UPDATE_AVAILABLE = "update available"
    ERROR = "error"


def user_data_dir() -> Path:
    """Return the per-user data directory for Gambit Pairing.

    ``GAMBIT_PAIRING_DATA_DIR`` overrides the platform location, which follows
    the same conventions as the log directory in ``utils.logging``.
    """
    override = os.environ.get(DATA_DIR_ENV)
    if override:
        return Path(override)
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", tempfile.gettempdir())
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    return Path(base) / "gambit-pairing"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def name_key(name: str) -> str:
    """Return a search key for ``name``: lower case, no accents or punctuation.

    The key starts with a space so a SQL ``LIKE '% word%'`` matches the start
    of any word.
    """
    decomposed = unicodedata.normalize("NFKD", name)
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    words = _NAME_KEY_STRIP.sub(" ", plain.casefold()).split()
    return " " + " ".join(words) if words else ""


@dataclass
class ListMetadata:
    """The record kept beside each downloaded list."""

    schema_version: int = PLAYER_LIST_SCHEMA_VERSION
    source_url: str = ""
    last_modified: str = ""
    etag: str = ""
    content_length: Optional[int] = None
    downloaded_at: str = ""
    row_count: Optional[int] = None
    skipped: dict[str, int] = field(default_factory=dict)
    checked_at: str = ""
    update_available: bool = False
    last_error: str = ""

    @classmethod
    def from_dict(cls, data: Any) -> "ListMetadata":
        if not isinstance(data, dict):
            return cls()
        known = {item.name for item in fields(cls)}
        return cls(**{key: value for key, value in data.items() if key in known})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def skipped_total(self) -> int:
        return sum(int(count) for count in self.skipped.values())


def parse_timestamp(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def is_check_due(
    metadata: ListMetadata,
    now: datetime,
    interval_seconds: int = PLAYER_LIST_CHECK_INTERVAL_SECONDS,
) -> bool:
    """Return True when a list was last checked ``interval_seconds`` ago or more."""
    checked = parse_timestamp(metadata.checked_at)
    if checked is None:
        return True
    return (now - checked).total_seconds() >= interval_seconds


def md5_from_etag(etag: str) -> Optional[str]:
    """Return the MD5 digest an ETag carries, if it is a bare MD5 (as CFC's is)."""
    match = _MD5_ETAG.match(etag.strip())
    return match.group(1).lower() if match else None


def atomic_write_text(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` through a temporary file in the same folder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(
        dir=path.parent, prefix=path.name + ".", suffix=TEMP_SUFFIX
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temp_name, path)
    except BaseException:
        remove_quietly(Path(temp_name))
        raise


def remove_quietly(path: Optional[Path]) -> None:
    if path is None:
        return
    with contextlib.suppress(FileNotFoundError):
        path.unlink()


class PlayerListStore:
    """Read and write the player lists kept in one data directory."""

    def __init__(
        self,
        data_dir: Optional[Path | str] = None,
        min_rows: int = PLAYER_LIST_MIN_ROWS,
        max_row_drop: float = PLAYER_LIST_MAX_ROW_DROP,
    ) -> None:
        base = Path(data_dir) if data_dir is not None else user_data_dir()
        self.root = base / PLAYER_LISTS_DIR_NAME
        self.min_rows = min_rows
        self.max_row_drop = max_row_drop

    # --- paths -------------------------------------------------------------

    def list_dir(self, spec: PlayerListSpec) -> Path:
        return self.root / spec.key

    def data_path(self, spec: PlayerListSpec) -> Path:
        return self.list_dir(spec) / spec.file_name

    def index_path(self, spec: PlayerListSpec) -> Path:
        return self.list_dir(spec) / INDEX_FILE_NAME

    def metadata_path(self, spec: PlayerListSpec) -> Path:
        return self.list_dir(spec) / METADATA_FILE_NAME

    def remove_stale_temp_files(self, spec: PlayerListSpec, now: datetime) -> None:
        folder = self.list_dir(spec)
        if not folder.is_dir():
            return
        for path in folder.glob("*" + TEMP_SUFFIX):
            with contextlib.suppress(OSError):
                if now.timestamp() - path.stat().st_mtime > STALE_TEMP_SECONDS:
                    path.unlink()

    def new_temp_path(self, spec: PlayerListSpec, suffix: str = TEMP_SUFFIX) -> Path:
        folder = self.list_dir(spec)
        folder.mkdir(parents=True, exist_ok=True)
        handle, name = tempfile.mkstemp(
            dir=folder, prefix=spec.file_name + ".", suffix=suffix
        )
        os.close(handle)
        return Path(name)

    # --- selection ---------------------------------------------------------

    def selected_keys(self) -> tuple[str, ...]:
        """Return the lists the user keeps, or ``DEFAULT_PLAYER_LISTS``."""
        path = self.root / SELECTION_FILE_NAME
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            keys = data.get("selected") if isinstance(data, dict) else None
        except (OSError, ValueError):
            keys = None
        if not isinstance(keys, list):
            keys = list(DEFAULT_PLAYER_LISTS)
        return tuple(key for key in keys if key in PLAYER_LISTS_BY_KEY)

    def selected_specs(self) -> tuple[PlayerListSpec, ...]:
        selected = set(self.selected_keys())
        return tuple(spec for spec in PLAYER_LISTS if spec.key in selected)

    def save_selection(self, keys: Iterable[str]) -> None:
        """Store the selection and delete local copies of deselected lists."""
        selected = [spec.key for spec in PLAYER_LISTS if spec.key in set(keys)]
        atomic_write_text(
            self.root / SELECTION_FILE_NAME,
            json.dumps({"selected": selected}, indent=2),
        )
        for spec in PLAYER_LISTS:
            if spec.key not in selected:
                self.remove(spec)

    def remove(self, spec: PlayerListSpec) -> None:
        folder = self.list_dir(spec)
        if folder.is_dir():
            shutil.rmtree(folder, ignore_errors=True)

    # --- metadata and state ------------------------------------------------

    def read_metadata(self, spec: PlayerListSpec) -> ListMetadata:
        try:
            data = json.loads(self.metadata_path(spec).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return ListMetadata()
        return ListMetadata.from_dict(data)

    def write_metadata(self, spec: PlayerListSpec, metadata: ListMetadata) -> None:
        atomic_write_text(
            self.metadata_path(spec), json.dumps(metadata.to_dict(), indent=2)
        )

    def has_data_file(self, spec: PlayerListSpec) -> bool:
        return self.data_path(spec).is_file()

    def is_downloaded(self, spec: PlayerListSpec) -> bool:
        """Return True when the list and an up-to-date index are on disk."""
        metadata = self.read_metadata(spec)
        return (
            bool(metadata.downloaded_at)
            and metadata.schema_version == PLAYER_LIST_SCHEMA_VERSION
            and self.has_data_file(spec)
            and self.index_path(spec).is_file()
        )

    def state(self, spec: PlayerListSpec) -> ListState:
        metadata = self.read_metadata(spec)
        if metadata.last_error:
            return ListState.ERROR
        if not self.is_downloaded(spec):
            return ListState.NOT_DOWNLOADED
        if metadata.update_available:
            return ListState.UPDATE_AVAILABLE
        return ListState.DOWNLOADED

    def describe_state(self, spec: PlayerListSpec) -> str:
        """Return the state text shown in the Player Lists dialog."""
        state = self.state(spec)
        metadata = self.read_metadata(spec)
        copy = ""
        downloaded = parse_timestamp(metadata.downloaded_at)
        if downloaded and self.is_downloaded(spec):
            copy = (
                f"{downloaded.astimezone():%Y-%m-%d}, "
                f"{metadata.row_count or 0:,} players"
            )
        if state is ListState.ERROR:
            kept = f" (keeping the copy from {copy})" if copy else ""
            return f"Error: {metadata.last_error}{kept}"
        if state is ListState.UPDATE_AVAILABLE:
            return f"Update available (current copy {copy})"
        if state is ListState.DOWNLOADED:
            return f"Downloaded {copy}"
        return "Not downloaded"

    def describe_skipped(self, spec: PlayerListSpec) -> str:
        """Return which rows the parser skipped in the stored copy, if any."""
        metadata = self.read_metadata(spec)
        if not metadata.skipped:
            return ""
        reasons = ", ".join(
            f"{count:,} {reason}"
            for reason, count in sorted(
                metadata.skipped.items(), key=lambda item: -item[1]
            )
        )
        return f"{metadata.skipped_total:,} rows skipped: {reasons}"

    def downloaded_specs(self, source: str) -> tuple[PlayerListSpec, ...]:
        return tuple(
            spec
            for spec in PLAYER_LISTS
            if spec.source == source and self.is_downloaded(spec)
        )

    def due_for_check(
        self,
        now: datetime,
        interval_seconds: int = PLAYER_LIST_CHECK_INTERVAL_SECONDS,
    ) -> tuple[PlayerListSpec, ...]:
        """Return the selected lists whose last check is older than the interval."""
        return tuple(
            spec
            for spec in self.selected_specs()
            if is_check_due(self.read_metadata(spec), now, interval_seconds)
        )

    # --- install -----------------------------------------------------------

    def install(
        self,
        spec: PlayerListSpec,
        temp_path: Path,
        headers: dict[str, str],
        now: datetime,
        cancelled: Optional[Callable[[], bool]] = None,
    ) -> ListMetadata:
        """Validate a downloaded file and move it over the stored copy.

        ``headers`` are the response headers of the download. On any failure
        the temporary files are removed, the stored copy is left untouched and
        :class:`PlayerListValidationError` is raised.
        """
        previous = self.read_metadata(spec)
        index_temp: Optional[Path] = None
        try:
            validate_file(spec, temp_path, headers)
            index_temp = self.new_temp_path(spec, suffix=".index" + TEMP_SUFFIX)
            report = build_index(spec, temp_path, index_temp, cancelled)
            self.validate_row_count(report, previous.row_count)
            os.replace(temp_path, self.data_path(spec))
            os.replace(index_temp, self.index_path(spec))
        except (PlayerListValidationError, OperationCancelled):
            remove_quietly(temp_path)
            remove_quietly(index_temp)
            raise
        except Exception as error:
            remove_quietly(temp_path)
            remove_quietly(index_temp)
            raise PlayerListValidationError(str(error)) from error

        metadata = ListMetadata(
            source_url=spec.url,
            last_modified=headers.get("last-modified", ""),
            etag=headers.get("etag", ""),
            content_length=_int_header(headers, "content-length"),
            downloaded_at=now.isoformat(),
            row_count=report.rows,
            skipped=dict(report.skipped),
            checked_at=now.isoformat(),
        )
        self.write_metadata(spec, metadata)
        logger.info("Installed %s: %s", spec.name, report.summary())
        return metadata

    def reindex(self, spec: PlayerListSpec) -> None:
        """Rebuild the search index from the stored file (after a schema bump)."""
        index_temp = self.new_temp_path(spec, suffix=".index" + TEMP_SUFFIX)
        try:
            report = build_index(spec, self.data_path(spec), index_temp)
            os.replace(index_temp, self.index_path(spec))
        except Exception:
            remove_quietly(index_temp)
            raise
        metadata = self.read_metadata(spec)
        metadata.schema_version = PLAYER_LIST_SCHEMA_VERSION
        metadata.row_count = report.rows
        metadata.skipped = dict(report.skipped)
        self.write_metadata(spec, metadata)

    def validate_row_count(
        self, report: ParseReport, previous_rows: Optional[int]
    ) -> None:
        if report.rows < self.min_rows:
            raise PlayerListValidationError(
                f"Only {report.rows:,} rows could be read; expected at least "
                f"{self.min_rows:,}"
            )
        if previous_rows:
            floor = previous_rows * (1 - self.max_row_drop)
            if report.rows < floor:
                raise PlayerListValidationError(
                    f"The new list has {report.rows:,} rows, down from "
                    f"{previous_rows:,}; keeping the old copy"
                )

    # --- queries -----------------------------------------------------------

    @contextlib.contextmanager
    def connect(self, spec: PlayerListSpec) -> Iterator[sqlite3.Connection]:
        """Open the list's index read-only."""
        uri = self.index_path(spec).resolve().as_uri() + "?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()


def _int_header(headers: dict[str, str], name: str) -> Optional[int]:
    value = headers.get(name, "").strip()
    return int(value) if value.isdigit() else None


def validate_file(spec: PlayerListSpec, path: Path, headers: dict[str, str]) -> None:
    """Check size, archive integrity and (for CFC) the MD5 ETag of a download."""
    expected = _int_header(headers, "content-length")
    actual = path.stat().st_size
    encoded = headers.get("content-encoding", "identity").lower() != "identity"
    if expected is not None and not encoded and actual != expected:
        raise PlayerListValidationError(
            f"Downloaded {actual:,} bytes but the server announced {expected:,}"
        )
    if actual == 0:
        raise PlayerListValidationError("The downloaded file is empty")

    if spec.is_zip:
        try:
            with zipfile.ZipFile(path) as archive:
                bad_member = archive.testzip()
        except zipfile.BadZipFile as error:
            raise PlayerListValidationError(
                f"The download is not a valid zip file: {error}"
            ) from error
        if bad_member is not None:
            raise PlayerListValidationError(f"CRC check failed for {bad_member}")

    digest = md5_from_etag(headers.get("etag", ""))
    if digest and not encoded:
        actual_digest = _file_md5(path)
        if actual_digest != digest:
            raise PlayerListValidationError(
                "The download does not match the server's MD5 checksum"
            )


def _file_md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# --- index -------------------------------------------------------------------

FIDE_TABLE = "fide_players"
CFC_TABLE = "cfc_members"

_FIDE_COLUMNS = (
    "fide_id",
    "name",
    "name_key",
    "federation",
    "sex",
    "title",
    "standard",
    "rapid",
    "blitz",
    "birth_year",
    "inactive",
)
_CFC_COLUMNS = (
    "cfc_id",
    "first",
    "last",
    "name_key",
    "expiry",
    "province",
    "city",
    "rating",
    "high",
    "active_rating",
    "active_high",
    "fide_id",
    "fide_rating",
)


def build_index(
    spec: PlayerListSpec,
    data_path: Path,
    index_path: Path,
    cancelled: Optional[Callable[[], bool]] = None,
) -> ParseReport:
    """Parse ``data_path`` into a fresh SQLite index at ``index_path``."""
    report = ParseReport()
    remove_quietly(index_path)
    connection = sqlite3.connect(index_path)
    try:
        connection.execute("PRAGMA journal_mode=OFF")
        connection.execute("PRAGMA synchronous=OFF")
        if spec.format == FORMAT_FIDE_XML_ZIP:
            _build_fide_index(connection, spec, data_path, report, cancelled)
        elif spec.format == FORMAT_CFC_TDLIST:
            _build_cfc_index(connection, data_path, report, cancelled)
        else:
            raise PlayerListValidationError(f"Unknown list format {spec.format}")
        connection.commit()
    finally:
        connection.close()
    return report


def _build_fide_index(
    connection: sqlite3.Connection,
    spec: PlayerListSpec,
    data_path: Path,
    report: ParseReport,
    cancelled: Optional[Callable[[], bool]],
) -> None:
    connection.execute(
        f"CREATE TABLE {FIDE_TABLE} (fide_id INTEGER PRIMARY KEY, name TEXT, "
        "name_key TEXT, federation TEXT, sex TEXT, title TEXT, standard INTEGER, "
        "rapid INTEGER, blitz INTEGER, birth_year INTEGER, inactive INTEGER)"
    )
    rows = (
        (
            player["fide_id"],
            player["name"],
            name_key(player["name"]),
            player["federation"],
            player["sex"],
            player["title"],
            player["standard"],
            player["rapid"],
            player["blitz"],
            player["birth_year"],
            int(player["inactive"]),
        )
        for player in iter_fide_players(data_path, report, spec.rating_kind)
    )
    _insert_batches(connection, FIDE_TABLE, _FIDE_COLUMNS, rows, cancelled)


def _build_cfc_index(
    connection: sqlite3.Connection,
    data_path: Path,
    report: ParseReport,
    cancelled: Optional[Callable[[], bool]],
) -> None:
    connection.execute(
        f"CREATE TABLE {CFC_TABLE} (cfc_id INTEGER PRIMARY KEY, first TEXT, "
        "last TEXT, name_key TEXT, expiry TEXT, province TEXT, city TEXT, "
        "rating INTEGER, high INTEGER, active_rating INTEGER, active_high INTEGER, "
        "fide_id INTEGER, fide_rating INTEGER)"
    )
    rows = (
        (
            member["cfc_id"],
            member["first"],
            member["last"],
            # Surname first, like FIDE names, so both rank the same way.
            name_key(f"{member['last']} {member['first']}"),
            member["expiry"],
            member["province"],
            member["city"],
            member["rating"],
            member["high"],
            member["active_rating"],
            member["active_high"],
            member["fide_id"],
            member["fide_rating"],
        )
        for member in iter_cfc_members(data_path, report)
    )
    _insert_batches(connection, CFC_TABLE, _CFC_COLUMNS, rows, cancelled)
    connection.execute(f"CREATE INDEX {CFC_TABLE}_fide_id ON {CFC_TABLE}(fide_id)")


def _insert_batches(
    connection: sqlite3.Connection,
    table: str,
    columns: tuple[str, ...],
    rows: Iterable[tuple[Any, ...]],
    cancelled: Optional[Callable[[], bool]] = None,
) -> None:
    statement = (
        f"INSERT INTO {table} ({', '.join(columns)}) "
        f"VALUES ({', '.join('?' for _ in columns)})"
    )
    batch: list[tuple[Any, ...]] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= INDEX_BATCH_SIZE:
            if cancelled and cancelled():
                raise OperationCancelled()
            connection.executemany(statement, batch)
            batch.clear()
    if batch:
        connection.executemany(statement, batch)
