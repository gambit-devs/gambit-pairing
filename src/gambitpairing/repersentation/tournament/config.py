"""Backward-compatible aliases for misspelled representation imports."""

from gambitpairing.representation.tournament import (
    tournament_config_from_dict,
    tournament_config_to_dict,
)

__all__ = ["tournament_config_from_dict", "tournament_config_to_dict"]
