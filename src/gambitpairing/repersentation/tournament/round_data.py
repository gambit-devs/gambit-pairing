"""Backward-compatible aliases for misspelled representation imports."""

from gambitpairing.representation.tournament import (
    round_data_from_dict,
    round_data_to_dict,
)

__all__ = ["round_data_from_dict", "round_data_to_dict"]
