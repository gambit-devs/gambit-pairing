"""Representations for TournamentConfig."""

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


from typing import Any, Dict, List

from gambitpairing.constants import DEFAULT_TIEBREAK_SORT_ORDER
from gambitpairing.models.tournament.tournament_config import TournamentConfig


def tournament_config_to_dict(config: TournamentConfig) -> Dict[str, Any]:
    """Project TournamentConfig into a dictionary representation.

    This function converts a :class:`~gambitpairing.models.tournament.tournament_config.TournamentConfig`
    domain object into a plain dictionary composed only of Python
    primitives. The resulting representation is suitable for storage,
    logging, undo/redo snapshots, and export.

    Parameters
    ----------
    config : TournamentConfig
        Tournament configuration domain object.

    Returns
    -------
    dict
        Dictionary representation of the tournament configuration.

    Notes
    -----
    This function performs no I/O and has no side effects. It is intended
    to be a pure projection of domain state.

    See Also
    --------
    tournament_config_from_dict : Reconstruct a TournamentConfig from its
        dictionary representation.
    """
    return {
        "name": config.name,
        "num_rounds": config.num_rounds,
        "pairing_system": config.pairing_system,
        "tiebreak_order": list(config.tiebreak_order),
        "tournament_over": config.tournament_over,
    }


def tournament_config_from_dict(data: Dict[str, Any]) -> TournamentConfig:
    """Reconstruct TournamentConfig from a dictionary representation.

    Parameters
    ----------
    data : dict
        Dictionary representation of tournament configuration data, as
        produced by :func:`tournament_config_to_dict`.

    Returns
    -------
    TournamentConfig
        Reconstructed tournament configuration domain object.

    Raises
    ------
    KeyError
        If required fields are missing from the input dictionary.

    Notes
    -----
    This function assumes the input dictionary is trusted and already
    validated at a higher layer. No validation is performed here.

    Default values are applied for optional fields to preserve backward
    compatibility with older representations.

    See Also
    --------
    tournament_config_to_dict : Convert a TournamentConfig into a
        dictionary representation.
    """
    return TournamentConfig(
        name=data.get("name", "Untitled Tournament"),
        num_rounds=data["num_rounds"],
        pairing_system=data.get("pairing_system", "dutch_swiss"),
        tiebreak_order=data.get(
            "tiebreak_order", list(DEFAULT_TIEBREAK_SORT_ORDER)
        ),
        tournament_over=data.get("tournament_over", False),
