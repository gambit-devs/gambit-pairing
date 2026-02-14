"""Round management for tournaments.

This module handles all round-related operations including pairing generation,
round progression, and round history management.
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

from typing import Callable, Dict, List, Optional, Tuple

from gambitpairing.controllers.pairing import (
    create_dutch_swiss_pairings,
    RoundRobin,
    create_round_robin,
)
from gambitpairing.models.player import Player
from gambitpairing.models.tournament import PairingHistory, RoundData
from gambitpairing.type_hints import Pairings
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


class RoundManager:
    """Manages round progression and pairing generation for tournaments.

    This class is responsible for:
    - Generating pairings based on the tournament's pairing system
    - Tracking round history
    - Managing round state transitions
    - Coordinating with pairing algorithms
    """

    def __init__(
        self,
        pairing_system: str,
        num_rounds: int,
        pairing_history: PairingHistory,
    ):
        """Initialize the round manager.

        Args:
            pairing_system: The pairing system to use ('dutch_swiss', 'round_robin', 'manual')
            num_rounds: Total number of rounds in the tournament
            pairing_history: History of pairings to prevent repeats
        """
        self.pairing_system = pairing_system
        self.num_rounds = num_rounds
        self.pairing_history = pairing_history
        self.rounds: List[RoundData] = []
        self.round_robin: Optional[RoundRobin] = None

    @property
    def current_round_number(self) -> int:
        """Get the current round number (1-indexed).

        Returns:
            The current round number, or 0 if no rounds have been created.
        """
        return len(self.rounds)

    @property
    def completed_rounds_count(self) -> int:
        """Get the number of completed rounds.

        Returns:
            Count of rounds that have had results recorded.
        """
        return sum(1 for round_data in self.rounds if round_data.is_completed)

    def get_round(self, round_number: int) -> Optional[RoundData]:
        """Get data for a specific round.

        Args:
            round_number: The round number (1-indexed)

        Returns:
            RoundData for the specified round, or None if invalid round number
        """
        if 1 <= round_number <= len(self.rounds):
            return self.rounds[round_number - 1]
        return None

    def create_next_round(
        self,
        players: Dict[str, Player],
        bye_callback: Optional[Callable] = None,
        repeat_pairing_callback: Optional[Callable] = None,
    ) -> Tuple[List[Tuple[Player, Player]], Optional[Player]]:
        """Generate pairings for the next round.

        Args:
            players: Dictionary of all tournament players (id -> Player)
            bye_callback: Optional callback to determine bye player
            repeat_pairing_callback: Optional callback for handling repeat pairings

        Returns:
            Tuple of (pairings list, bye player)
            pairings is a list of (white_player, black_player) tuples

        Raises:
            ValueError: If all rounds have already been created
            NotImplementedError: If pairing system is not supported
        """
        if len(self.rounds) >= self.num_rounds:
            raise ValueError(
                f"Cannot create more rounds: already at {self.num_rounds} rounds"
            )

        round_number = len(self.rounds) + 1
        active_players = [p for p in players.values() if p.is_active]

        logger.info(
            f"Creating round {round_number} with {len(active_players)} active players"
        )

        if self.pairing_system == "dutch_swiss":
            pairings, bye_player = self._create_swiss_pairings(
                active_players, round_number, bye_callback, repeat_pairing_callback
            )
        elif self.pairing_system == "round_robin":
            pairings, bye_player = self._create_round_robin_pairings(
                active_players, round_number
            )
        elif self.pairing_system == "manual":
            pairings, bye_player = self._create_manual_pairings()
        else:
            raise NotImplementedError(
                f"Pairing system '{self.pairing_system}' is not implemented"
            )

        # Create round data
        pairing_ids = [(white.id, black.id) for white, black in pairings]
        bye_id = bye_player.id if bye_player else None

        round_data = RoundData(
            round_number=round_number, pairings=pairing_ids, bye_player_id=bye_id
        )

        self.rounds.append(round_data)

        # Update pairing history
        for white, black in pairings:
            self.pairing_history.add_pairing(white.id, black.id)

        return pairings, bye_player

    def _create_swiss_pairings(
        self,
        active_players: List[Player],
        round_number: int,
        bye_callback: Optional[Callable],
        repeat_pairing_callback: Optional[Callable],
    ) -> Tuple[List[Tuple[Player, Player]], Optional[Player]]:
        """Create pairings using Dutch Swiss system."""
        pairings, bye_player, pairing_ids, bye_id = create_dutch_swiss_pairings(
            active_players,
            round_number,
            self.pairing_history.previous_matches,
            bye_callback,
            repeat_pairing_callback,
            self.num_rounds,
        )
        return pairings, bye_player

    def _create_round_robin_pairings(
        self, active_players: List[Player], round_number: int
    ) -> Tuple[List[Tuple[Player, Player]], Optional[Player]]:
        """Create pairings using Round Robin system."""
        # Initialize round robin on first call
        if self.round_robin is None:
            self.round_robin = create_round_robin(active_players)
            # Update num_rounds to match round robin requirements
            if self.num_rounds != self.round_robin.number_of_rounds:
                logger.info(
                    f"Updating tournament rounds from {self.num_rounds} to "
                    f"{self.round_robin.number_of_rounds} for round robin"
                )
                self.num_rounds = self.round_robin.number_of_rounds

        pairings, bye_player = self.round_robin.get_round_pairings(round_number)
        return pairings, bye_player

    def _create_manual_pairings(
        self,
    ) -> Tuple[List[Tuple[Player, Player]], Optional[Player]]:
        """Create empty pairings for manual entry."""
        return [], None

    def set_manual_pairings(
        self,
        round_number: int,
        pairings: List[Tuple[Player, Player]],
        bye_player: Optional[Player],
    ) -> bool:
        """Set manual pairings for a specific round.

        Args:
            round_number: The round number (1-indexed)
            pairings: List of (white_player, black_player) tuples
            bye_player: Player receiving bye, or None

        Returns:
            True if successful, False otherwise
        """
        if round_number < 1:
            logger.error(f"Invalid round number: {round_number}")
            return False

        # Ensure we have enough rounds
        while len(self.rounds) < round_number:
            self.rounds.append(RoundData(round_number=len(self.rounds) + 1))

        round_data = self.rounds[round_number - 1]

        # Update pairings
        round_data.pairings = [(white.id, black.id) for white, black in pairings]
        round_data.bye_player_id = bye_player.id if bye_player else None

        # Update pairing history
        for white, black in pairings:
            self.pairing_history.add_pairing(white.id, black.id)

        logger.info(
            f"Set manual pairings for round {round_number}: "
            f"{len(pairings)} pairings, bye: {bye_player.name if bye_player else 'None'}"
        )
        return True

    def mark_round_completed(self, round_number: int) -> bool:
        """Mark a round as completed.

        Args:
            round_number: The round number (1-indexed)

        Returns:
            True if successful, False if round doesn't exist
        """
        round_data = self.get_round(round_number)
        if round_data is None:
            logger.error(f"Cannot mark non-existent round {round_number} as completed")
            return False

        round_data.is_completed = True
        logger.info(f"Round {round_number} marked as completed")
        return True

    def undo_last_round(self) -> bool:
        """Remove the last round if it hasn't been completed.

        Returns:
            True if successful, False if no rounds or last round is completed
        """
        if not self.rounds:
            logger.warning("Cannot undo: no rounds exist")
            return False

        last_round = self.rounds[-1]
        if last_round.is_completed:
            logger.warning(f"Cannot undo completed round {last_round.round_number}")
            return False

        # Remove pairings from history
        for white_id, black_id in last_round.pairings:
            pair = frozenset({white_id, black_id})
            self.pairing_history.previous_matches.discard(pair)

        self.rounds.pop()
        logger.info(f"Undid round {last_round.round_number}")
        return True

    def get_pairings_for_display(
        self, round_number: int, players: Dict[str, Player]
    ) -> Tuple[List[Tuple[Player, Player]], Optional[Player]]:
        """Get pairings for a round with Player objects for display.

        Args:
            round_number: The round number (1-indexed)
            players: Dictionary of all players (id -> Player)

        Returns:
            Tuple of (pairings list, bye player) with Player objects
        """
        round_data = self.get_round(round_number)
        if round_data is None:
            return [], None

        pairings = []
        for white_id, black_id in round_data.pairings:
            white = players.get(white_id)
            black = players.get(black_id)
            if white and black:
                pairings.append((white, black))

        bye_player = (
            players.get(round_data.bye_player_id) if round_data.bye_player_id else None
        )
        return pairings, bye_player
