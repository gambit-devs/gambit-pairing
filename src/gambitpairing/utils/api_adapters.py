"""API Adapters for converting API responses to Player objects.

This module provides adapter functions that convert raw API responses
from various chess federations into properly validated Player objects
using the factory pattern.
"""

from datetime import date
from typing import Any, Dict, List, Optional

from gambitpairing.models.player import create_player
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


def fide_api_to_player_dict(fide_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert FIDE API response to player dictionary for factory.

    Args:
        fide_data: Raw data from FIDE API search results

    Returns:
        Dictionary compatible with create_player_from_dict()

    Example:
        >>> fide_data = {
        ...     "fide_id": "123456",
        ...     "name": "Doe, John",
        ...     "title": "GM",
        ...     "federation": "USA",
        ...     "standard_rating": 2500,
        ...     "rapid_rating": 2450,
        ...     "blitz_rating": 2400,
        ...     "birth_year": 1990,
        ...     "gender": "M"
        ... }
        >>> player_dict = fide_api_to_player_dict(fide_data)
        >>> player = create_player_from_dict(player_dict)
    """
    # Convert FIDE ID to integer
    fide_id = None
    if fide_data.get("fide_id"):
        try:
            fide_id = int(str(fide_data["fide_id"]).strip())
        except (ValueError, TypeError):
            logger.warning("Invalid FIDE ID: %s", fide_data.get("fide_id"))

    # Parse name (FIDE format is usually "Last, First")
    name = fide_data.get("name", "").strip()

    # Parse birth year to date of birth
    date_of_birth = None
    birth_year = fide_data.get("birth_year")
    if birth_year:
        try:
            # Set to January 1st of birth year
            year = int(birth_year)
            if 1900 <= year <= date.today().year:
                date_of_birth = date(year, 1, 1)
        except (ValueError, TypeError):
            logger.debug("Could not parse birth year: %s", birth_year)

    # Use standard rating as primary, fall back to rapid/blitz
    rating = (
        fide_data.get("standard_rating")
        or fide_data.get("rapid_rating")
        or fide_data.get("blitz_rating")
        or 0
    )

    return {
        "name": name,
        "rating": rating,
        "fide_id": fide_id,
        "fide_title": fide_data.get("title"),
        "fide_standard": fide_data.get("standard_rating"),
        "fide_rapid": fide_data.get("rapid_rating"),
        "fide_blitz": fide_data.get("blitz_rating"),
        "federation": fide_data.get("federation"),
        "gender": fide_data.get("gender"),
        "date_of_birth": date_of_birth,
    }


def cfc_api_to_player_dict(cfc_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert CFC API response to player dictionary for factory.

    Args:
        cfc_data: Raw data from CFC API player endpoint

    Returns:
        Dictionary compatible with create_player_from_dict()

    Example:
        >>> cfc_data = {
        ...     "cfc_id": 123456,
        ...     "name_first": "John",
        ...     "name_last": "Doe",
        ...     "regular_rating": 1800,
        ...     "addr_city": "Toronto",
        ...     "addr_province": "ON"
        ... }
        >>> player_dict = cfc_api_to_player_dict(cfc_data)
        >>> player = create_player_from_dict(player_dict)
    """
    # Combine first and last name
    first_name = cfc_data.get("name_first", "").strip()
    last_name = cfc_data.get("name_last", "").strip()
    name = f"{first_name} {last_name}".strip()

    # Use regular rating as primary, fall back to quick rating
    rating = cfc_data.get("regular_rating") or cfc_data.get("quick_rating") or 0

    # Build location string from city and province
    city = cfc_data.get("addr_city", "").strip()
    province = cfc_data.get("addr_province", "").strip()
    location = f"{city}, {province}" if city and province else (city or province)

    # FIDE ID if available
    fide_id = cfc_data.get("fide_id")
    if fide_id and fide_id != 0:
        fide_id = int(fide_id)
    else:
        fide_id = None

    player_dict = {
        "name": name,
        "rating": rating,
        "federation": "CAN",  # CFC is Canadian federation
    }

    # Add FIDE ID if present
    if fide_id:
        player_dict["fide_id"] = fide_id

    # Add location as club if available
    if location:
        player_dict["club"] = location

    return player_dict


def fide_profile_to_player_dict(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert FIDE profile page data to player dictionary.

    This is used when get_fide_player_info returns detailed profile data.

    Args:
        profile_data: Parsed FIDE profile data

    Returns:
        Dictionary compatible with create_player_from_dict()
    """
    # Similar to search results but may have more detailed info
    return fide_api_to_player_dict(profile_data)


def api_response_to_players(
    api_responses: List[Dict[str, Any]], source: str = "fide"
) -> List[Any]:  # Returns List[Player]
    """Convert list of API responses to Player objects.

    Batch conversion with error handling for individual failures.

    Args:
        api_responses: List of API response dictionaries
        source: API source ('fide', 'cfc', 'uscf')

    Returns:
        List of Player objects (may be shorter than input if some fail)

    Example:
        >>> from gambitpairing.utils.api import search_fide_players
        >>> api_results = search_fide_players("Carlsen")
        >>> players = api_response_to_players(api_results, source="fide")
    """
    # Import here to avoid circular dependency
    from gambitpairing.models.player import create_player_from_dict

    # Select appropriate adapter
    if source.lower() == "fide":
        adapter = fide_api_to_player_dict
    elif source.lower() == "cfc":
        adapter = cfc_api_to_player_dict
    else:
        logger.warning("Unknown API source: %s, using FIDE adapter", source)
        adapter = fide_api_to_player_dict

    players = []
    for api_data in api_responses:
        try:
            player_dict = adapter(api_data)
            player = create_player_from_dict(player_dict)
            players.append(player)
        except Exception as e:
            logger.warning(
                "Failed to create player from API data: %s - %s",
                api_data.get("name", "Unknown"),
                e,
            )
            continue

    return players


def create_player_from_fide_search(fide_data: Dict[str, Any]) -> Optional[Any]:
    """Create a single Player from FIDE search result.

    Convenience function for single player creation.

    Args:
        fide_data: Single FIDE API search result

    Returns:
        Player object or None if creation fails
    """
    from gambitpairing.models.player import create_player_from_dict

    try:
        player_dict = fide_api_to_player_dict(fide_data)
        return create_player_from_dict(player_dict)
    except Exception as e:
        logger.error("Failed to create player from FIDE data: %s", e)
        return None


def create_player_from_cfc_data(cfc_data: Dict[str, Any]) -> Optional[Any]:
    """Create a single Player from CFC API response.

    Convenience function for single player creation.

    Args:
        cfc_data: Single CFC API player response

    Returns:
        Player object or None if creation fails
    """
    from gambitpairing.models.player import create_player_from_dict

    try:
        player_dict = cfc_api_to_player_dict(cfc_data)
        return create_player_from_dict(player_dict)
    except Exception as e:
        logger.error("Failed to create player from CFC data: %s", e)
        return None


# Convenience exports for common use cases
__all__ = [
    "fide_api_to_player_dict",
    "cfc_api_to_player_dict",
    "fide_profile_to_player_dict",
    "api_response_to_players",
    "create_player_from_fide_search",
    "create_player_from_cfc_data",
]
