"""Main Tournament class - orchestrates all tournament operations.

This is the primary interface for tournament management, coordinating various
specialized managers to provide a clean, professional API.
"""

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
from __future__ import annotations
import functools
from typing import Any, Callable, Dict, List, Optional, Tuple

from dataclasses import dataclass, field
from gambitpairing.constants import LOSS_SCORE, WIN_SCORE
from gambitpairing.models.player import Player
from .pairing_history import PairingHistory
from .round_data import RoundData
from .tournament_config import TournamentConfig


from gambitpairing.type_hints import Pairings
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


@dataclass
class Tournament:
    """Main tournament management class.

    This class coordinates all tournament operations through specialized managers:
    - RoundManager: handles round creation and pairing
    - ResultRecorder: manages result entry and validation
    - TiebreakCalculator: computes tiebreak scores

    The Tournament class maintains the overall state and provides a clean API
    for tournament operations.
    """

    def __init__(
        self,
        name: str,
        players: List[Player],
        num_rounds: int,
        tiebreak_order: Optional[List[str]] = None,
        pairing_system: str = "dutch_swiss",
    ) -> None:
        """Initialize a new tournament.

        Args
        ----
        name: Tournament name
        players: List of participating players
        num_rounds: Number of rounds to play
        tiebreak_order: Priority order for tiebreak criteria
        pairing_system: Pairing system ('dutch_swiss', 'round_robin', 'manual')
        """
        # Configuration
        self.config = TournamentConfig(
            name=name,
            num_rounds=num_rounds,
            pairing_system=pairing_system,
            tiebreak_order=tiebreak_order,
        )

        # Players
        self.players: Dict[str, Player] = {p.id: p for p in players}

        # Pairing history
        self.pairing_history = PairingHistory()

        # Specialized managers
        self.round_manager = RoundManager(
            pairing_system=self.config.pairing_system,
            num_rounds=self.config.num_rounds,
            pairing_history=self.pairing_history,
        )
        self.result_recorder = ResultRecorder()
        self.tiebreak_calculator = TiebreakCalculator()

    # ========== Properties ==========

    @property
    def name(self) -> str:
        """Get tournament name."""
        return self.config.name

    @name.setter
    def name(self, value: str) -> None:
        """Set tournament name."""
        self.config.name = value

    @property
    def num_rounds(self) -> int:
        """Get number of rounds."""
        return self.config.num_rounds

    @num_rounds.setter
    def num_rounds(self, value: int) -> None:
        """Set number of rounds."""
        self.config.num_rounds = value
        # Update the round manager with the new number of rounds
        self.round_manager.num_rounds = value

    @property
    def pairing_system(self) -> str:
        """Get pairing system."""
        return self.config.pairing_system

    @property
    def tiebreak_order(self) -> List[str]:
        """Get tiebreak order."""
        return self.config.tiebreak_order

    @tiebreak_order.setter
    def tiebreak_order(self, value: List[str]) -> None:
        """Set tiebreak order."""
        self.config.tiebreak_order = value

    @property
    def tournament_over(self) -> bool:
        """Is the tournament over?"""
        return self.config.tournament_over

    @tiebreak_order.setter
    def tournament_over(self, value: bool) -> None:
        """Set tournament over."""
        self.config.tournament_over = value
