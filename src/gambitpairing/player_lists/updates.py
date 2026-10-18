"""Check player lists for changes and download new copies.

A check is a conditional ``HEAD`` request (``If-None-Match`` and
``If-Modified-Since`` from the stored metadata). Both the FIDE and CFC servers
answer it with ``304 Not Modified`` when nothing changed, so a check never
transfers the list. The list itself is only downloaded when the server reports
a change or there is no usable local copy.
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

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import httpx

from gambitpairing import APP_NAME, APP_VERSION
from gambitpairing.player_lists.catalog import PlayerListSpec
from gambitpairing.player_lists.store import (
    ListMetadata,
    OperationCancelled,
    PlayerListStore,
    PlayerListValidationError,
    remove_quietly,
    utc_now,
)
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)

HTTP_TIMEOUT_SECONDS = 30.0
DOWNLOAD_CHUNK_SIZE = 256 * 1024

# (bytes done, bytes expected or None)
ProgressCallback = Callable[[int, Optional[int]], None]
StatusCallback = Callable[[str], None]
CancelledCallback = Callable[[], bool]


class CheckStatus(Enum):
    UNCHANGED = "unchanged"
    UPDATED = "updated"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(frozen=True)
class CheckOutcome:
    key: str
    status: CheckStatus
    message: str = ""


def create_http_client() -> httpx.Client:
    """Return the client used for list checks and downloads."""
    return httpx.Client(
        timeout=HTTP_TIMEOUT_SECONDS,
        follow_redirects=True,
        headers={"User-Agent": f"{APP_NAME.replace(' ', '')}/{APP_VERSION}"},
    )


def conditional_headers(metadata: ListMetadata) -> dict[str, str]:
    """Return the validators that turn a request into a conditional one."""
    headers: dict[str, str] = {}
    if metadata.etag:
        headers["If-None-Match"] = metadata.etag
    if metadata.last_modified:
        headers["If-Modified-Since"] = metadata.last_modified
    return headers


def server_reports_change(response: httpx.Response, metadata: ListMetadata) -> bool:
    """Decide from a check response whether the server copy differs from ours.

    A 304 means unchanged. A 200 is compared against the stored validators in
    case a server or proxy ignores the conditional headers.
    """
    if response.status_code == 304:
        return False
    etag = response.headers.get("etag", "")
    if etag and metadata.etag:
        return etag != metadata.etag
    last_modified = response.headers.get("last-modified", "")
    length = response.headers.get("content-length", "")
    if last_modified and metadata.last_modified:
        same_length = (
            not length
            or metadata.content_length is None
            or length == str(metadata.content_length)
        )
        return not (last_modified == metadata.last_modified and same_length)
    return True


def check_and_update(
    store: PlayerListStore,
    spec: PlayerListSpec,
    client: httpx.Client,
    force: bool = False,
    progress: Optional[ProgressCallback] = None,
    cancelled: Optional[CancelledCallback] = None,
    now: Optional[datetime] = None,
    status: Optional[StatusCallback] = None,
) -> CheckOutcome:
    """Check one list and download it when it changed or is missing.

    ``force`` is "Update now": it skips nothing here (the 24-hour throttle is
    applied by the caller when choosing lists) but still uses a conditional
    check, so an unchanged list is not downloaded again.
    """
    now = now or utc_now()
    report_status = status or (lambda _text: None)
    metadata = store.read_metadata(spec)
    try:
        store.remove_stale_temp_files(spec, now)
        if (
            store.has_data_file(spec)
            and metadata.downloaded_at
            and not store.is_downloaded(spec)
        ):
            # The stored file predates the current index schema.
            report_status(f"{spec.name}: rebuilding the search index")
            store.reindex(spec)
            metadata = store.read_metadata(spec)

        have_copy = store.is_downloaded(spec)
        if have_copy:
            report_status(f"{spec.name}: checking for changes")
            response = client.head(spec.url, headers=conditional_headers(metadata))
            if response.status_code not in (200, 304):
                raise PlayerListValidationError(
                    f"{spec.name}: the server answered {response.status_code}"
                )
            if not server_reports_change(response, metadata):
                metadata.checked_at = now.isoformat()
                metadata.update_available = False
                metadata.last_error = ""
                store.write_metadata(spec, metadata)
                return CheckOutcome(spec.key, CheckStatus.UNCHANGED, "Up to date")
            metadata.update_available = True
            store.write_metadata(spec, metadata)

        if cancelled and cancelled():
            return CheckOutcome(spec.key, CheckStatus.CANCELLED, "Cancelled")
        temp_path, headers = download_to_temp(
            store, spec, client, progress=progress, cancelled=cancelled
        )
        report_status(f"{spec.name}: checking the download and building the index")
        store.install(spec, temp_path, headers, now, cancelled)
        installed = store.read_metadata(spec)
        return CheckOutcome(
            spec.key,
            CheckStatus.UPDATED,
            f"Downloaded {installed.row_count or 0:,} players",
        )
    except OperationCancelled:
        return CheckOutcome(spec.key, CheckStatus.CANCELLED, "Cancelled")
    except (httpx.HTTPError, PlayerListValidationError, OSError) as error:
        message = _error_text(error)
        logger.warning("Player list %s: %s", spec.key, message)
        failed = store.read_metadata(spec)
        failed.checked_at = now.isoformat()
        failed.last_error = message
        try:
            store.write_metadata(spec, failed)
        except OSError:
            logger.exception("Could not record the player list error")
        return CheckOutcome(spec.key, CheckStatus.FAILED, message)


def download_to_temp(
    store: PlayerListStore,
    spec: PlayerListSpec,
    client: httpx.Client,
    progress: Optional[ProgressCallback] = None,
    cancelled: Optional[CancelledCallback] = None,
) -> tuple[Path, dict[str, str]]:
    """Download ``spec`` into a temporary file beside the stored copy."""
    temp_path = store.new_temp_path(spec)
    try:
        # Ask for the file as stored so Content-Length and the MD5 ETag
        # describe the bytes written to disk. If a server compresses anyway,
        # the bytes are decoded and validation skips those two checks.
        with client.stream(
            "GET", spec.url, headers={"Accept-Encoding": "identity"}
        ) as response:
            response.raise_for_status()
            headers = {key.lower(): value for key, value in response.headers.items()}
            expected = response.headers.get("content-length", "")
            total = int(expected) if expected.isdigit() else None
            done = 0
            with temp_path.open("wb") as stream:
                for chunk in response.iter_bytes(DOWNLOAD_CHUNK_SIZE):
                    if cancelled and cancelled():
                        raise OperationCancelled()
                    stream.write(chunk)
                    done += len(chunk)
                    if progress:
                        progress(done, total)
    except BaseException:
        remove_quietly(temp_path)
        raise
    return temp_path, headers


def _error_text(error: Exception) -> str:
    if isinstance(error, httpx.TimeoutException):
        return "The server did not respond in time"
    if isinstance(error, httpx.ConnectError):
        return "Could not connect to the server (are you offline?)"
    if isinstance(error, httpx.HTTPStatusError):
        return f"The server answered {error.response.status_code}"
    return str(error) or error.__class__.__name__


def format_progress(spec: PlayerListSpec, done: int, total: Optional[int]) -> str:
    """Return text such as ``"FIDE combined: downloading 12.5 of 48.3 MB"``."""
    megabytes = done / 1_000_000
    if total:
        return f"{spec.name}: downloading {megabytes:.1f} of {total / 1_000_000:.1f} MB"
    return f"{spec.name}: downloading {megabytes:.1f} MB"
