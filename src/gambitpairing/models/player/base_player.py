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

from dataclasses import dataclass, field
from typing import Optional, List

from gambitpairing.models.enums import Colour
from gambitpairing.models.federation import Federation


@dataclass(slots=True)
class Player(PlayerABC):
    """
    Concrete player implementation used by tournament pairing systems.

    This class represents the canonical, mutable player entity used internally
    by pairing algorithms (e.g. FIDE Dutch Swiss). It implements the
    :class:`PlayerABC` interface and stores all tournament-related state
    required for pairing, color assignment, floating, and result tracking.

    The player identifier (``id``) is immutable by design, while all other
    attributes may be updated as the tournament progresses.

    Attributes
    ----------
    id : str
        Immutable unique identifier for the player.
    name : str
        Player's full name.
    rating : int
        Player's rating used for initial seeding and tie-breaking.
    federation : Federation
        Federation the player belongs to (e.g. FIDE, national federation).
    phone : str or None
        Validated phone number, if available.
    email : str or None
        Validated email address, if available.
    score : float
        Current tournament score.
    pairing_number : int or None
        Pairing number assigned for the tournament. Used for deterministic
        ordering and tie-breaking.
    is_active : bool
        Whether the player is currently active in the tournament.
    color_history : list of Colour or None
        Chronological list of colors played by the player in each round.
        ``None`` entries indicate byes.
    match_history : list of dict
        Per-round match metadata, including opponent IDs and scores.
    results : list of float or None
        Per-round results from the player's perspective.
    is_moved_down : bool
        Indicates whether the player was moved down from a higher score
        bracket in the current pairing computation.
    float_history : list of int
        Rounds in which the player floated (up or down), used to minimize
        repeat floats.
    has_received_bye : bool
        Whether the player has already received a bye.
    bsn : int or None
        Bracket Sequential Number (BSN) assigned during pairing computations
        to ensure FIDE-compliant ordering.

    Notes
    -----
    - This class is intentionally **free of pairing logic**.
    - All pairing decisions are handled by pairing system
      implementations, not by the player object itself.
    - Instances are lightweight and memory-efficient due to `slots=True`.
    - New attributes cannot be added dynamically.

    Examples
    --------
    Creating a player::

        player = Player(
            _id="p-001",
            name="Nicolas Vaagen",
            rating=1850,
            federation=Federation.FIDE,
        )

    Updating tournament state::

        player.score += 1.0
        player.color_history.append(Colour.WHITE)
        player.results.append(1.0)

    Using polymorphically::

        def print_player(p: PlayerABC) -> None:
            print(p)

        print_player(player)

    See Also
    --------
    PlayerABC
        Abstract interface implemented by all player types.
    PairingSystemABC
        Interface used by pairing algorithms operating on players.
    """

    _id: str
    name: str
    rating: int
    federation: Federation

    phone: Optional[str] = None
    email: Optional[str] = None

    # Tournament state (mutable)
    score: float = 0.0
    pairing_number: Optional[int] = None
    is_active: bool = True

    # History tracking (used heavily by Dutch Swiss)
    colour_history: List[Optional[Colour]] = field(default_factory=list)
    match_history: List[dict] = field(default_factory=list)
    results: List[Optional[float]] = field(default_factory=list)

    # Float tracking
    is_moved_down: bool = False
    float_history: List[int] = field(default_factory=list)
    has_received_bye: bool = False

    @property
    def id(self) -> str:
        """Immutable player identifier."""
        return self._id
