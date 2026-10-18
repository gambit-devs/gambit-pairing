"""Utilities for looking up players from chess federation endpoints.

This module provides helper functions to retrieve player information from
chess federation sources over HTTP.
"""

# Copyright (C) 2024  Nicolas Vaagen
#
# This program is free software.

from typing import Any, Dict, List

import httpx

from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)

# URL stubs for API endpoints
CFC_URL_STUB = "https://server.chess.ca/"


def get_cfc_player_info(cfc_id: str) -> Dict[str, Any]:
    """Retrieve player information from CFC API.

    Gets player details including name, rating and membership status
    from the Chess Federation of Canada API.

    Parameters
    ----------
    cfc_id : str
        The CFC ID number of the player to look up.

    Returns
    -------
    dict - JSON response from the API.
        example:
        {'updated': '2025-04-24',
        'player': {
            'cfc_id': 123123,
            'cfc_expiry': '2020-01-02',
            'fide_id': 0,
            'name_first': 'Michael',
            'name_last': 'Williams',
            'addr_city': "St.John's",
            'addr_province': 'NL',
            'regular_rating': 200,
            'regular_indicator': 11,
            'quick_rating': 200,
            'quick_indicator': 11,
            'events': [{'id': 199806005,
                'name': 'MacDonald Dr RR',
                'date_end': '1998-05-14',
                'rating_type': 'R',
                'games_played': 11,
                'score': 0.0,
                'rating_pre': 0,
                'rating_perf': 0,
                'rating_post': 200,
                'rating_indicator': 11}],
            'orgarb': [],
            'is_organizer': False,
            'is_arbiter': False
        },
        'apicode': 0,
        'error': ''}

        Player information from the API response.
        Contains fields like name, rating, expiry date, etc.

    Raises
    ------
    httpx.exceptions.RequestException
        If the API request fails for any reason
    ValueError
        If the response is not valid JSON
    """
    cfc_id = str(cfc_id).strip()
    if not cfc_id:
        raise ValueError("A CFC ID is required")
    api_path = f"/api/player/v1/{cfc_id}"

    try:
        r = httpx.get(
            f"{CFC_URL_STUB.rstrip('/')}{api_path}",
            timeout=10.0,
        )
        r.raise_for_status()

        api_info = r.json()
        logger.debug("CFC API response: %s", api_info)

        player = api_info.get("player") if isinstance(api_info, dict) else None
        if not isinstance(player, dict) or not player.get("name_last"):
            raise ValueError(f"{api_path} did not return a player")

        return player

    except httpx.HTTPError as e:
        raise httpx.HTTPError(f"HTTP error: {e}") from e


def get_uscf_player_info(uscf_id):
    """Get the player info from uscf API.

    Todo
    ----
    Implement
    """
    raise NotImplementedError("TODO: tried to get uscf player info for id: %s", uscf_id)


# TODO: Implement
def get_fide_top_players(count: int = 50) -> List[Dict[str, Any]]:
    """Get top-rated FIDE players.

    This function is currently not implemented and returns an empty list.

    Parameters
    ----------
    count : int, default 50
        Number of top players to return

    Returns
    -------
    List[Dict[str, Any]]
        Empty list (function not implemented)
    """
    logger.error(f"Getting top {count} FIDE players - not implemented")
    return []


#  LocalWords:  apicode RUS CHN
