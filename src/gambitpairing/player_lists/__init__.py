"""Locally kept FIDE and CFC player lists and the player search built on them.

This package is Qt-free. The GUI drives it from
``gambitpairing.gui.player_list_workflow``.
"""

from gambitpairing.player_lists.catalog import (
    PLAYER_LISTS,
    SOURCE_CFC,
    SOURCE_FIDE,
    PlayerListSpec,
    get_player_list,
)
from gambitpairing.player_lists.store import (
    ListMetadata,
    ListState,
    PlayerListStore,
    PlayerListValidationError,
    user_data_dir,
)

__all__ = [
    "PLAYER_LISTS",
    "SOURCE_CFC",
    "SOURCE_FIDE",
    "ListMetadata",
    "ListState",
    "PlayerListSpec",
    "PlayerListStore",
    "PlayerListValidationError",
    "get_player_list",
    "user_data_dir",
]
