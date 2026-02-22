"""Factory for creating Player objects with validation.

This module implements the Factory pattern for Player creation,
providing a single point of entry for creating players with
proper validation and error handling.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional

from gambitpairing.exceptions import InvalidPlayerDataException
from gambitpairing.models.player.base_player import Player
from gambitpairing.utils.validation import (
    validate_email,
    validate_fide_id,
    validate_name,
    validate_phone,
    validate_rating,
)

from .base_player import Player
from .fide_player import FidePlayer


class PlayerFactory:
    """Factory for creating Player and FidePlayer instances.

    This class provides methods to create players with proper validation
    and error handling. It encapsulates the complexity of determining
    whether to create a Player or FidePlayer based on the provided data.

    Example
    -------
        >>> factory = PlayerFactory()
        >>> player = factory.create_player(name="John Doe", rating=1800)
        >>> fide_player = factory.create_player(
        ...     name="Jane Smith",
        ...     fide_id="123456",
        ...     fide_standard=2100
        ... )
    """

    def __init__(self, validate: bool = True, strict: bool = False):
        """Initialize the PlayerFactory.

        Parameters
        ----------
        validate : bool
            Whether to validate input data
        strict : bool
            Whether to raise exceptions on validation errors
        """
        self.validate = validate
        self.strict = strict

    def create_player(
        self,
        name: str,
        rating: Optional[int] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        gender: Optional[str] = None,
        date_of_birth: Optional[date] = None,
        federation: Optional[str] = None,
        fide_id: Optional[int] = None,  # Changed from str to int
        fide_title: Optional[str] = None,
        fide_standard: Optional[int] = None,
        fide_rapid: Optional[int] = None,
        fide_blitz: Optional[int] = None,
        **kwargs,
    ) -> "Player":
        """Create a Player or FidePlayer based on provided data.

        Automatically determines whether to create a Player or FidePlayer
        based on whether FIDE-specific data is provided.

        Parameters
        ----------
            name: Player's name
            rating: Player's rating
            phone: Phone number
            email: Email address
            club: Chess club
            gender: Gender
            date_of_birth: Date of birth
            federation: Chess federation
            fide_id: FIDE ID (integer)
            fide_title: FIDE title
            fide_standard: FIDE standard rating
            fide_rapid: FIDE rapid rating
            fide_blitz: FIDE blitz rating
            **kwargs: Additional parameters

        Returns
        -------
            Player or FidePlayer instance

        Raises
        ------
            InvalidPlayerDataException: If validation fails and strict=True
        """
        # Import here to avoid circular imports

        # Validate data if enabled
        if self.validate:
            validation_errors = self._validate_data(
                name=name,
                rating=rating,
                phone=phone,
                email=email,
                fide_id=str(fide_id) if fide_id is not None else None,
            )

            if validation_errors and self.strict:
                error_msg = "; ".join(validation_errors)
                raise InvalidPlayerDataException(f"Invalid player data: {error_msg}")

        # Determine if this should be a FidePlayer
        has_fide_data = any(
            [
                fide_id,
                fide_title,
                fide_standard,
                fide_rapid,
                fide_blitz,
            ]
        )

        if has_fide_data:
            return FidePlayer(
                name=name,
                rating=rating,
                phone=phone,
                email=email,
                club=club,
                gender=gender,
                date_of_birth=date_of_birth,
                federation=federation,
                fide_id=fide_id,
                fide_title=fide_title,
                fide_standard=fide_standard,
                fide_rapid=fide_rapid,
                fide_blitz=fide_blitz,
                **kwargs,
            )
        else:
            return Player(
                name=name,
                rating=rating,
                phone=phone,
                email=email,
                club=club,
                gender=gender,
                date_of_birth=date_of_birth,
                federation=federation,
                **kwargs,
            )

    def create_from_dict(self, data: Dict[str, Any]) -> "Player":
        """Create a player from dictionary data.

        Parameters
        ----------
            data: Dictionary containing player data

        Returns
        -------
            Player or FidePlayer instance

        Raises
        ------
            InvalidPlayerDataException: If required fields are missing
        """
        if "name" not in data:
            raise InvalidPlayerDataException("Player name is required")

        # Check if this is FIDE player data
        has_fide_data = any(
            [
                data.get("fide_id"),
                data.get("fide_title"),
                data.get("fide_standard"),
                data.get("fide_rapid"),
                data.get("fide_blitz"),
            ]
        )

        if has_fide_data:
            return FidePlayer.from_dict(data)
        else:
            return Player.from_dict(data)

    def create_batch(self, player_data_list: list[Dict[str, Any]]) -> list["Player"]:
        """Create multiple players from a list of dictionaries.

        Parameters
        ----------
        player_data_list : list[Dict[str, Any]]
            List of dictionaries containing player data

        Returns
        -------
            List of Player/FidePlayer instances
        """
        players: list["Player"] = []
        for data in player_data_list:
            try:
                player = self.create_from_dict(data)
                players.append(player)
            except InvalidPlayerDataException as e:
                if self.strict:
                    raise
                # Log error and continue in non-strict mode
                print(f"Warning: Skipping invalid player data: {e}")

        return players


def _update_player_from_data(self, player: Player, data: dict) -> None:
    """Update a player object in-place from a data dictionary.

    Applies core attributes to all player types and additionally
    applies FIDE-specific attributes when the player is a
    ``FidePlayer`` instance. Uses ``setattr`` to avoid hard-coding
    individual field assignments.

    Parameters
    ----------
    player : Player
        The player object to update
    data : dict
        Dictionary containing updated player data
    """
    # Core attributes that all players have
    core_attrs = [
        "name",
        "rating",
        "phone",
        "email",
        "gender",
        "dob",
        "federation",
    ]

    # Update core attributes
    for attr in core_attrs:
        if attr in data:
            setattr(player, attr, data[attr])

    # Update FIDE-specific attributes if this is a FidePlayer
    if isinstance(player, FidePlayer):
        fide_attrs = [
            "fide_id",
            "fide_title",
            "fide_standard",
            "fide_rapid",
            "fide_blitz",
            "birth_year",
        ]
        for attr in fide_attrs:
            if attr in data and data.get(attr) is not None:
                setattr(player, attr, data[attr])

    def _validate_data(
        self,
        name: Optional[str],
        rating: Optional[int],
        phone: Optional[str],
        email: Optional[str],
        fide_id: Optional[str],
    ) -> list[str]:
        """Validate player data and return list of errors.

        Parameters
        ----------
        name : Optional[str]
            Player name
        rating : Optional[int]
            Player rating
        phone : Optional[str]
            Player phone number
        email : Optional[str]
            Email address
        fide_id : Optional[str]
            FIDE id

        Returns
        -------
            List of validation error messages
        """
        errors = []

        # Validate name
        name_result = validate_name(name, required=True)
        if not name_result:
            errors.append(name_result.error_message or "Invalid name")

        # Validate rating
        if rating is not None:
            rating_result = validate_rating(rating)
            if not rating_result:
                errors.append(rating_result.error_message or "Invalid rating")

        # Validate phone
        if phone:
            phone_result = validate_phone(phone)
            if not phone_result:
                errors.append(phone_result.error_message or "Invalid phone")

        # Validate email
        if email:
            email_result = validate_email(email)
            if not email_result:
                errors.append(email_result.error_message or "Invalid email")

        # Validate FIDE ID
        if fide_id:
            fide_result = validate_fide_id(fide_id)
            if not fide_result:
                errors.append(fide_result.error_message or "Invalid FIDE ID")

        return errors


# Global factory instance for convenience
default_factory = PlayerFactory(validate=True, strict=False)


def create_player(**kwargs) -> "Player":
    """Create a player using the default factory.

    Parameters
    ----------
        **kwargs: Player attributes

    Returns
    -------
        Player or FidePlayer instance

    Examples
    --------
        >>> player = create_player(name="John Doe", rating=1800)
    """
    return default_factory.create_player(**kwargs)


def create_player_from_dict(data: Dict[str, Any]) -> "Player":
    """Create a player from dict using default factory.

    Parameters
    ----------
    data : Dict[str, Any]
        Dictionary containing player data

    Returns
    -------
    Player
        created player
    """
    return default_factory.create_from_dict(data)


#  LocalWords:  PlayerFactory
