"""Representations for Tournament."""

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

from gambitpairing.models.tournament.tournament import Tournament

from gambitpairing.representation.tournament.config import (
    tournament_config_to_dict,
    tournament_config_from_dict,
)
from gambitpairing.representation.tournament.round_data import (
    round_data_to_dict,
    round_data_from_dict,
)
from gambitpairing.representation.tournament.pairing_history import (
    pairing_history_to_dict,
    pairing_history_from_dict,
)
from gambitpairing.representation.player import (
    player_to_dict,
    player_from_dict,
)


def tournament_to_dict(tournament: Tournament) -> Dict[str, Any]:
    """Project a Tournament into a dictionary representation.

    This function converts a :class:`~gambitpairing.models.tournament.tournament.Tournament`
    aggregate into a plain dictionary composed only of Python primitives.
    The resulting representation is suitable for storage, logging,
    undo/redo snapshots, and export.

    Parameters
    ----------
    tournament : Tournament
        Tournament stored in the dict.

    Returns
    -------
    dict
        Dictionary representation of the tournament.

    Notes
    -----
    This function performs no I/O and has no side effects. It is intended
    to be a pure projection of domain state.

    The representation is *lossless*: a tournament reconstructed via
    :func:`tournament_from_dict` will be semantically equivalent.

    See Also
    --------
    tournament_from_dict : Reconstruct a Tournament from its dictionary
        representation.
    """
    return {
        "__version__": 1,
        "config": tournament_config_to_dict(tournament.config),
        "players": {
            player_id: player_to_dict(player)
            for player_id, player in tournament.players.items()
        },
        "rounds": [round_data_to_dict(r) for r in tournament.rounds],
        "pairing_history": pairing_history_to_dict(tournament.pairing_history),
    }


def tournament_from_dict(data: Dict[str, Any]) -> Tournament:
    """Reconstruct a Tournament from a dictionary representation.

    Parameters
    ----------
    data : dict
        Dictionary representation of a tournament, as produced by
        :func:`tournament_to_dict`.

    Returns
    -------
    Tournament
        Reconstructed tournament aggregate root.

    Raises
    ------
    KeyError
        If required fields are missing from the input dictionary.

    Notes
    -----
    This function assumes the input dictionary is trusted and already
    validated at a higher layer. No validation is performed here.

    The ``__version__`` field is reserved for future representation
    migrations. Currently, only version ``1`` is supported.

    See Also
    --------
    tournament_to_dict : Convert a Tournament into a dictionary
        representation.
    """
    version = data.get("__version__", 1)
    if version != 1:
        raise ValueError(f"Unsupported tournament representation version: {version}")

    config = tournament_config_from_dict(data["config"])

    players = [player_from_dict(pdata) for pdata in data.get("players", {}).values()]

    tournament = Tournament(
        name=config.name,
        players=players,
        num_rounds=config.num_rounds,
        tiebreak_order=config.tiebreak_order,
        pairing_system=config.pairing_system,
    )

    tournament.config.tournament_over = config.tournament_over

    tournament.rounds = [round_data_from_dict(r) for r in data.get("rounds", [])]

    tournament.pairing_history = pairing_history_from_dict(
        data.get("pairing_history", {})
    )

    return tournament
