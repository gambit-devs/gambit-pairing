"""Check GitHub Releases for a newer Gambit Pairing version.

This check is the single source of truth for "is a newer version available":
the tag of the latest (non-draft, non-prerelease) GitHub release, compared with
``gambitpairing._version.__version__`` using :mod:`packaging.version`.

Velopack only downloads and applies the update the user accepted. Release CI
packs every Velopack release with ``--packVersion`` equal to ``__version__`` and
requires the release tag to be ``v<__version__>``, and the Velopack updater
refuses to apply a package whose version differs from the one checked here.
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
from typing import Any

import httpx
from packaging.version import InvalidVersion, Version

from gambitpairing.constants import RELEASES_PAGE_URL, UPDATE_URL
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


class UpdateCheckError(Exception):
    """The latest release could not be retrieved or understood."""


@dataclass(frozen=True)
class ReleaseInfo:
    """The parts of a GitHub release the update prompt needs."""

    version: str
    tag: str
    notes: str
    page_url: str


def parse_version(text: str) -> Version | None:
    """Parse a release tag or version string such as ``v0.8.1``.

    Returns ``None`` for strings that are not valid versions.
    """
    candidate = text.strip()
    if candidate[:1] in ("v", "V"):
        candidate = candidate[1:]
    try:
        return Version(candidate)
    except InvalidVersion:
        return None


def is_newer_version(candidate: str, current: str) -> bool:
    """Return True when ``candidate`` is a strictly newer version than ``current``.

    Unparseable versions never count as newer, so a malformed tag cannot
    trigger an update prompt.
    """
    candidate_version = parse_version(candidate)
    current_version = parse_version(current)
    if candidate_version is None or current_version is None:
        return False
    return candidate_version > current_version


def release_from_payload(payload: dict[str, Any]) -> ReleaseInfo:
    """Build a :class:`ReleaseInfo` from a GitHub release API payload."""
    tag = str(payload.get("tag_name") or "")
    version = parse_version(tag)
    if version is None:
        raise UpdateCheckError(f"Latest release tag {tag!r} is not a valid version")
    if payload.get("draft") or payload.get("prerelease"):
        raise UpdateCheckError(f"Release {tag} is a draft or prerelease")
    return ReleaseInfo(
        version=str(version),
        tag=tag,
        notes=str(payload.get("body") or "No description available."),
        page_url=str(payload.get("html_url") or RELEASES_PAGE_URL),
    )


def fetch_latest_release(
    url: str = UPDATE_URL,
    client_factory: Callable[..., httpx.Client] = httpx.Client,
) -> ReleaseInfo:
    """Fetch the latest GitHub release.

    Raises
    ------
    UpdateCheckError
        On network errors, HTTP errors, or a malformed response.
    """
    try:
        with client_factory(timeout=10.0, follow_redirects=True) as client:
            response = client.get(
                url, headers={"Accept": "application/vnd.github+json"}
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise UpdateCheckError(f"Could not reach GitHub Releases: {error}") from error
    if not isinstance(payload, dict):
        raise UpdateCheckError("Unexpected response from GitHub Releases")
    return release_from_payload(payload)


def find_newer_release(
    current_version: str,
    fetch: Callable[[], ReleaseInfo] = fetch_latest_release,
) -> ReleaseInfo | None:
    """Return the latest release when it is newer than ``current_version``."""
    release = fetch()
    newer = is_newer_version(release.version, current_version)
    logger.info(
        "Latest release: %s, current version: %s, newer available: %s",
        release.version,
        current_version,
        newer,
    )
    return release if newer else None
