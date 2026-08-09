"""Compatibility exports for the manual-pairing controller projections.

The projections used to live beside the Qt dialog.  Keep this import path for
third-party callers while the implementation lives in the Qt-free controller
layer.
"""

from gambitpairing.controllers.pairing.manual_pairing_controller import (
    ValidationProjection,
    accounted_player_ids,
    active_unpaired_players,
    build_stats_text,
    build_unresolved_players_message,
    build_validation_projection,
    incomplete_pairing_count,
    paired_player_count,
    repeat_pairing_boards,
    unresolved_active_players,
)

__all__ = [
    "ValidationProjection",
    "active_unpaired_players",
    "accounted_player_ids",
    "build_stats_text",
    "build_unresolved_players_message",
    "build_validation_projection",
    "incomplete_pairing_count",
    "paired_player_count",
    "repeat_pairing_boards",
    "unresolved_active_players",
]
