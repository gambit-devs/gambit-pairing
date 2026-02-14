"""Chess federation data class."""

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

from dataclasses import dataclass
from typing import ClassVar, Dict


@dataclass(frozen=True, slots=True)
class Federation:
    """
    Chess federation descriptor.

    Parameters
    ----------
    code : str
        Short federation code (e.g. ``"FIDE"``, ``"USCF"``).
    name : str
        Human-readable federation name.
    """

    code: str
    name: str

    # ---- predefined registry (Enum replacement) ----
    _REGISTRY: ClassVar[Dict[str, "Federation"]] = {}

    def __post_init__(self) -> None:
        """Register the Federation code in self._REGISTRY."""
        # Normalize code
        object.__setattr__(self, "code", self.code.upper())

        # Register federation
        if self.code in self._REGISTRY:
            raise ValueError(f"Federation '{self.code}' already registered")
        self._REGISTRY[self.code] = self

    def __str__(self) -> str:
        """Representation as a str just the Federation code."""
        return self.code

    def __repr__(self) -> str:
        """Representation of all the data."""
        return f"Federation(code='{self.code}', name='{self.name}')"

    @classmethod
    def from_code(cls, code: str) -> "Federation":
        """Lookup a Federation from code. Codes are: FIDE, USCF, CFC."""
        try:
            return cls._REGISTRY[code.upper()]
        except KeyError as exc:
            raise ValueError(f"Unknown federation code: {code}") from exc
