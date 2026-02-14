"""A base chess player in a tournament. This is a base class."""

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


from abc import ABC, abstractmethod
from typing import Optional


class PlayerABC(ABC):
    """Abstract interface for a Player."""

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

    @property
    @abstractmethod
    def club(self):
        """Club association (or None)."""
        raise NotImplementedError

    #
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
