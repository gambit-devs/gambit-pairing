"""Download and apply updates with Velopack, on platforms where that is enabled.

Velopack reads releases from GitHub through ``velopack.GithubSource``. Only
the platforms in :data:`IN_APP_UPDATE_PLATFORMS` update in place; elsewhere
the update prompt opens the release page instead. Add a ``sys.platform`` value
to that set to enable in-app updates for another platform once its release
job publishes a Velopack feed.
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
import sys
from typing import Any

from gambitpairing.constants import RELEASES_REPOSITORY_URL
from gambitpairing.update.release_check import parse_version
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)

# sys.platform values whose packaged builds update in place through Velopack.
IN_APP_UPDATE_PLATFORMS = frozenset({"win32"})


class VelopackUpdateError(Exception):
    """Velopack could not provide the update that the release check found."""


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def in_app_update_supported(
    platform: str | None = None, frozen: bool | None = None
) -> bool:
    """Return True when this build may update itself through Velopack."""
    platform = sys.platform if platform is None else platform
    frozen = is_frozen() if frozen is None else frozen
    return frozen and platform in IN_APP_UPDATE_PLATFORMS


def _import_velopack() -> Any:
    import velopack

    return velopack


class VelopackUpdater:
    """Thin wrapper around ``velopack.UpdateManager`` for GitHub Releases."""

    def __init__(
        self,
        repository_url: str = RELEASES_REPOSITORY_URL,
        velopack_loader: Callable[[], Any] = _import_velopack,
    ) -> None:
        self._repository_url = repository_url
        self._velopack_loader = velopack_loader
        self._manager: Any = None
        self._pending: Any = None

    def _get_manager(self) -> Any:
        if self._manager is None:
            velopack = self._velopack_loader()
            # Stable releases only, matching the GitHub "latest release" check.
            source = velopack.GithubSource(self._repository_url, None, False)
            self._manager = velopack.UpdateManager(source)
        return self._manager

    def is_available(self) -> bool:
        """Return True when this app is a Velopack install that can update."""
        try:
            self._get_manager()
        except Exception as error:  # ImportError or "not installed" RuntimeError
            logger.info("Velopack updates unavailable: %s", error)
            return False
        return True

    def download(
        self,
        expected_version: str,
        progress_callback: Callable[[int], object] | None = None,
    ) -> str:
        """Download the update to ``expected_version`` and keep it pending.

        Raises
        ------
        VelopackUpdateError
            When Velopack finds no update, or a different version than the
            GitHub release check found.
        """
        manager = self._get_manager()
        info = manager.check_for_updates()
        if info is None:
            raise VelopackUpdateError(
                f"No Velopack package for version {expected_version} was found "
                "in the GitHub release."
            )
        target = str(info.TargetFullRelease.Version)
        if parse_version(target) != parse_version(expected_version):
            raise VelopackUpdateError(
                f"The release check found version {expected_version}, but the "
                f"Velopack feed offers {target}."
            )
        if progress_callback is None:
            manager.download_updates(info)
        else:
            manager.download_updates(info, progress_callback)
        self._pending = info
        return target

    def apply_and_restart(self) -> None:
        """Hand the pending update to Velopack's updater.

        Velopack waits for this process to exit, applies the update and starts
        the new version. The caller must close the application afterwards.
        """
        if self._pending is None:
            raise VelopackUpdateError("No downloaded update to apply")
        self._get_manager().wait_exit_then_apply_updates(
            self._pending, silent=False, restart=True
        )
