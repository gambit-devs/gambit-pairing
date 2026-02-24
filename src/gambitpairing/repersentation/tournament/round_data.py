"""Data transformation/serialization/to-from dict for RoundData."""

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

from typing import Any, Dict

from gambitpairing.models.tournament.round_data import RoundData
from gambitpairing.representation.tournament.match_result import (
    match_result_to_dict,
    match_result_from_dict,
)


def round_data_to_dict(round_data: RoundData) -> Dict[str, Any]:
    """Project RoundData into a dictionary representation.

    Parameters
    ----------
    round_data : RoundData
        Tournament round domain object.

    Returns
    -------
    dict
        Dictionary representation of the round.

    See Also
    --------
    round_data_from_dict : Reconstruct a RoundData from its dictionary
        representation.
    """
    return {
        "round_number": round_data.round_number,
        "pairings": round_data.pairings,
        "bye_player_id": round_data.bye_player_id,
        "results": [match_result_to_dict(r) for r in round_data.results],
        "is_completed": round_data.is_completed,
    }


def round_data_from_dict(data: Dict[str, Any]) -> RoundData:
    """Project RoundData into a dictionary representation.

    Parameters
    ----------
    round_data : RoundData
        Tournament round domain object.

    Returns
    -------
    dict
        Dictionary representation of the round.

    See Also
    --------
    round_data_to_dict : Create a RoundData dictionary representation.
    """
    return RoundData(
        round_number=data["round_number"],
        pairings=[tuple(p) for p in data.get("pairings", [])],
        bye_player_id=data.get("bye_player_id"),
        results=[match_result_from_dict(r) for r in data.get("results", [])],
        is_completed=data.get("is_completed", False),
    )


#  LocalWords:  RoundData
