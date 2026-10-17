"""Release checks (GitHub) and in-app updates (Velopack)."""

from gambitpairing.update.release_check import (
    ReleaseInfo,
    UpdateCheckError,
    fetch_latest_release,
    find_newer_release,
    is_newer_version,
    parse_version,
)
from gambitpairing.update.velopack_updater import (
    IN_APP_UPDATE_PLATFORMS,
    VelopackUpdateError,
    VelopackUpdater,
    in_app_update_supported,
)

__all__ = [
    "IN_APP_UPDATE_PLATFORMS",
    "ReleaseInfo",
    "UpdateCheckError",
    "VelopackUpdateError",
    "VelopackUpdater",
    "fetch_latest_release",
    "find_newer_release",
    "in_app_update_supported",
    "is_newer_version",
    "parse_version",
]
