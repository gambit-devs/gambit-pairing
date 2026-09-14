"""Round controller for tournaments.

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
    RoundRobin,
    create_dutch_swiss_pairings,
    create_round_robin,
)
from gambitpairing.controllers.pairing.bbp_dutch import (
    BBPPairingBackend,
    BBPPairingEngine,
    BBPPairingError,
    BBPUnavailableError,
)
from gambitpairing.models.player import Player
from gambitpairing.models.tournament import PairingHistory, RoundData
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


class RoundController:
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
        fide_strict: bool = False,
        bbp_engine: Optional[BBPPairingBackend] = None,
        use_experimental_dutch: bool = False,
        model=None,
    ):
        """Initialize the round manager.

        Args:
            pairing_system: The pairing system to use ('dutch_swiss',
                'round_robin', 'manual')
            num_rounds: Total number of rounds in the tournament
            pairing_history: History of pairings to prevent repeats
            fide_strict: Use stricter FIDE compliance search for Dutch Swiss
            bbp_engine: Optional BBP backend, primarily for dependency
                injection and tests
            use_experimental_dutch: Use Gambit's native Dutch engine directly
                instead of the primary BBP engine
        """
        if pairing_system == "bbp_dutch":
            # Keep callers of the short-lived separate BBP ID compatible while
            # keeping the controller's canonical state format-oriented.
            pairing_system = "dutch_swiss"
            use_experimental_dutch = False
        self.pairing_system = pairing_system
        self.num_rounds = num_rounds
        self.pairing_history = pairing_history
        self.fide_strict = fide_strict
        self.use_experimental_dutch = bool(use_experimental_dutch)
        self.bbp_engine = bbp_engine if bbp_engine is not None else BBPPairingEngine()
        self._model = model
        self._rounds: List[RoundData] = []
        self.round_robin: Optional[RoundRobin] = None
        self._round_robin_player_ids: Optional[Tuple[str, ...]] = None
        self.last_engine = pairing_system
        self.fallback_reason = None

    @property
    def rounds(self) -> List[RoundData]:
        return self._model.rounds if self._model is not None else self._rounds

    @rounds.setter
    def rounds(self, value: List[RoundData]) -> None:
        if self._model is not None:
            self._model.rounds = value
        else:
            self._rounds = value

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

        if any(not round_data.is_completed for round_data in self.rounds):
            raise ValueError("Complete the previous round before generating another")

        round_number = len(self.rounds) + 1
        self.last_engine = self.pairing_system
        self.fallback_reason = None
        active_players = [p for p in players.values() if p.is_active]

        logger.info(
            f"Creating round {round_number} with {len(active_players)} active players"
        )

        if self.pairing_system == "dutch_swiss":
            if self.use_experimental_dutch:
                pairings, bye_player = self._create_swiss_pairings(
                    active_players,
                    round_number,
                    bye_callback,
                    repeat_pairing_callback,
                )
            else:
                pairings, bye_player = self._create_bbp_pairings(
                    active_players,
                    round_number,
                    bye_callback,
                    repeat_pairing_callback,
                    all_players=list(players.values()),
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
            round_number=round_number,
            pairings=pairing_ids,
            bye_player_id=bye_id,
            active_player_ids=[player.id for player in active_players],
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
        """Create pairings using Gambit's experimental Dutch implementation."""
        return self._create_native_swiss_pairings(
            active_players,
            round_number,
            bye_callback,
            repeat_pairing_callback,
        )

    def _create_bbp_pairings(
        self,
        active_players: List[Player],
        round_number: int,
        bye_callback: Optional[Callable],
        repeat_pairing_callback: Optional[Callable],
        all_players: Optional[List[Player]] = None,
    ) -> Tuple[List[Tuple[Player, Player]], Optional[Player]]:
        """Create pairings with BBP, falling back to experimental Dutch."""
        try:
            result = self.bbp_engine.generate_pairings(
                active_players,
                current_round=round_number,
                total_rounds=self.num_rounds,
                all_players=all_players,
            )
            self.last_engine = "BBP Dutch"
            return result
        except BBPUnavailableError as error:
            self.fallback_reason = str(error)
            logger.info(
                "BBP Dutch unavailable; using Gambit Dutch (experimental): %s",
                error,
            )
        except BBPPairingError as error:
            self.fallback_reason = str(error)
            logger.warning(
                "BBP Dutch could not pair round %s; using Gambit Dutch (experimental): %s",
                round_number,
                error,
            )

        return self._create_native_swiss_pairings(
            active_players,
            round_number,
            bye_callback,
            repeat_pairing_callback,
        )

    def _create_native_swiss_pairings(
        self,
        active_players: List[Player],
        round_number: int,
        bye_callback: Optional[Callable],
        repeat_pairing_callback: Optional[Callable],
    ) -> Tuple[List[Tuple[Player, Player]], Optional[Player]]:
        """Create pairings using Gambit's native Dutch implementation."""
        self.last_engine = "Gambit Dutch (Experimental)"
        pairings, bye_player, _pairing_ids, _bye_id = create_dutch_swiss_pairings(
            active_players,
            round_number,
            self.pairing_history.previous_matches,
            bye_callback,
            repeat_pairing_callback,
            self.num_rounds,
            fide_strict=self.fide_strict,
        )
        return pairings, bye_player

    def _create_round_robin_pairings(
        self, active_players: List[Player], round_number: int
    ) -> Tuple[List[Tuple[Player, Player]], Optional[Player]]:
        """Create pairings using Round Robin system."""
        active_player_ids = tuple(player.id for player in active_players)
        if (
            self.round_robin is None
            or self._round_robin_player_ids != active_player_ids
        ):
            self.round_robin = create_round_robin(active_players)
            self._round_robin_player_ids = active_player_ids
            # Update num_rounds to match round robin requirements
            if self.num_rounds != self.round_robin.number_of_rounds:
                logger.info(
                    f"Updating tournament rounds from {self.num_rounds} to "
                    f"{self.round_robin.number_of_rounds} for round robin"
                )
                self.num_rounds = self.round_robin.number_of_rounds

        for schedule_round in range(1, self.round_robin.number_of_rounds + 1):
            pairings, bye_player = self.round_robin.get_round_pairings(schedule_round)
            if all(
                not self.pairing_history.have_played(white.id, black.id)
                for white, black in pairings
            ):
                return list(pairings), bye_player

        raise ValueError(
            f"No round-robin pairing is available for round {round_number} "
            "without repeating a pairing"
        )

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
        if (
            round_number < 1
            or round_number > self.num_rounds
            or round_number > len(self.rounds) + 1
        ):
            logger.error(f"Invalid round number: {round_number}")
            return False

        if any(not item.is_completed for item in self.rounds[: round_number - 1]):
            return False
        if (
            round_number <= len(self.rounds)
            and self.rounds[round_number - 1].is_completed
        ):
            return False
        assigned = [player.id for pair in pairings for player in pair]
        if bye_player is not None:
            assigned.append(bye_player.id)
        if len(set(assigned)) != len(assigned):
            return False

        # Ensure we have enough rounds
        while len(self.rounds) < round_number:
            self.rounds.append(RoundData(round_number=len(self.rounds) + 1))

        round_data = self.rounds[round_number - 1]

        new_pairs = {(white.id, black.id) for white, black in pairings}
        round_data.pending_results = [
            result
            for result in round_data.pending_results
            if (result.white_id, result.black_id) in new_pairs
        ]

        # Update pairings
        round_data.pairings = [(white.id, black.id) for white, black in pairings]
        round_data.bye_player_id = bye_player.id if bye_player else None

        # Update pairing history
        self.pairing_history.previous_matches = {
            frozenset(pair) for item in self.rounds for pair in item.pairings
        }

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
