"""Backward-compatible aliases for misspelled representation imports."""

from gambitpairing.representation.tournament import (
    match_result_from_dict,
    match_result_to_dict,
)

__all__ = ["match_result_from_dict", "match_result_to_dict"]
