"""An abstract base class representing a chess player in a tournament."""

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

# lets you refer to a type before it exists, deferring resolution until later.
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class PlayerABC(ABC):
    """
    Abstract base class defining the interface for a tournament player.

    This class specifies the required attributes and behavior for any concrete
    player implementation used throughout the system. It enforces a stable,
    read-only player identifier while allowing other attributes (such as rating
    or contact information) to be mutable in concrete implementations.

    Subclasses must implement all abstract properties defined here. This class
    also provides common string representations via ``__str__`` and ``__repr__``.

    Attributes
    ----------
    id : str
        Immutable unique identifier generated for internal use.
    name : str
        Player's full name.
    rating : int
        Player's rating.
    federation : Federation
        Player's federation (e.g. FIDE, CFC, or USCF).
    phone : str or None
        Validated phone number, if available.
    email : str or None
        Validated email address, if available.

    Notes
    -----
    - This class is an abstract interface and cannot be instantiated directly.
    - Attribute immutability is enforced at the interface level for ``id``.
    - Concrete implementations are responsible for validation of values such
      as email addresses, phone numbers, and ratings.
    - All subclasses inherit a consistent ``__str__`` and ``__repr__`` format
      unless explicitly overridden.

    Examples
    --------
    Implementing a concrete player class::

        @dataclass(slots=True)
        class Player(PlayerABC):
            _id: str
            name: str
            rating: int
            federation: Federation
            phone: str | None = None
            email: str | None = None

            @property
            def id(self) -> str:
                return self._id

    Using a player polymorphically::

        def print_player(player: PlayerABC) -> None:
            print(player)

        print_player(player)

    See Also
    --------
    Federation
        Federation type associated with a player. Is an enum in models/enums.py
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique identifier generated for internal use."""
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        """Player's full name."""
        raise NotImplementedError

    @property
    @abstractmethod
    def rating(self) -> int:
        """Player's rating."""
        raise NotImplementedError

    @property
    @abstractmethod
    def federation(self) -> Federation:
        """Player's rating."""
        raise NotImplementedError

    @property
    @abstractmethod
    def phone(self) -> Optional[str]:
        """Validated phone number."""
        raise NotImplementedError

    @property
    @abstractmethod
    def email(self) -> Optional[str]:
        """Validated email address."""
        raise NotImplementedError

    # concrete implementations so all inhered classes have a string representation
    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return f"Player(name='{self.name}', rating={self.rating}, id='{self.id}')"

    def __str__(self) -> str:
        """Return human-readable string representation.

        Example
        -------
            Nicolas (90001)
            Player name and rating
        """
        return f"{self.name} ({self.rating})"
