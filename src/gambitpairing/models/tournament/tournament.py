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

import functools
from typing import Any, Callable, Dict, List, Optional, Tuple

from gambitpairing.constants import LOSS_SCORE, WIN_SCORE
from gambitpairing.models.player import Player
from .pairing_history import PairingHistory
from .round_data import RoundData
from .tournament_config import TournamentConfig

from gambitpairing.controllers.tournament import (
    ResultRecorder,
    RoundManager,
    TiebreakCalculator,
)

from gambitpairing.type_hints import Pairings
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


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
        """Set tournament over"""
        self.config.tournament_over = value

    # ========== Player Management ==========

    def get_player_list(self, active_only: bool = False) -> List[Player]:
        """Get list of tournament players.

        Args:
            active_only: If True, only return active players

        Returns:
            List of Player objects
        """
        players = list(self.players.values())
        if active_only:
            return [p for p in players if p.is_active]
        return players

    def add_player(self, player: Player) -> None:
        """Add a player to the tournament.

        Args:
            player: Player to add
        """
        self.players[player.id] = player
        logger.info(f"Added player: {player.name} ({player.id})")

    def remove_player(self, player_id: str) -> bool:
        """Remove a player from the tournament.

        Args:
            player_id: ID of player to remove

        Returns:
            True if removed, False if not found
        """
        if player_id in self.players:
            player = self.players.pop(player_id)
            logger.info(f"Removed player: {player.name} ({player_id})")
            return True
        return False

    def set_player_active(self, player_id: str, is_active: bool) -> bool:
        """Set a player's active status.

        Args:
            player_id: ID of player
            is_active: New active status

        Returns:
            True if updated, False if player not found
        """
        player = self.players.get(player_id)
        if player:
            player.is_active = is_active
            logger.info(f"Set {player.name} active status to: {is_active}")
            return True
        return False

    # ========== Round Management ==========

    def create_pairings(
        self,
        current_round: int,
        allow_repeat_pairing_callback: Optional[Callable] = None,
    ) -> Pairings:
        """Generate pairings for the next round.

        Args:
            current_round: The round number being created (1-indexed)
            allow_repeat_pairing_callback: Optional callback for repeat pairing handling

        Returns:
            Tuple of (pairings list, bye player)
        """
        pairings, bye_player = self.round_manager.create_next_round(
            players=self.players,
            bye_callback=self._get_eligible_bye_player,
            repeat_pairing_callback=allow_repeat_pairing_callback,
        )

        logger.info(
            f"Created pairings for round {current_round}: "
            f"{len(pairings)} games, bye: {bye_player.name if bye_player else 'None'}"
        )

        return pairings, bye_player

    def get_pairings_for_round(self, round_index: int) -> Pairings:
        """Get pairings for a specific round.

        Args:
            round_index: Round index (0-indexed)

        Returns:
            Tuple of (pairings list, bye player)
        """
        round_number = round_index + 1
        return self.round_manager.get_pairings_for_display(round_number, self.players)

    def set_manual_pairings(
        self,
        round_index: int,
        pairings: List[Tuple[Player, Player]],
        bye_player: Optional[Player],
    ) -> bool:
        """Set manual pairings for a round.

        Args:
            round_index: Round index (0-indexed)
            pairings: List of (white, black) player pairs
            bye_player: Player receiving bye

        Returns:
            True if successful
        """
        round_number = round_index + 1
        return self.round_manager.set_manual_pairings(
            round_number, pairings, bye_player
        )

    # ========== Result Management ==========

    def record_results(
        self, round_index: int, results_data: List[Tuple[str, str, float]]
    ) -> bool:
        """Record results for a round.

        Args:
            round_index: Round index (0-indexed)
            results_data: List of (white_id, black_id, white_score) tuples

        Returns:
            True if all results recorded successfully
        """
        round_number = round_index + 1
        round_data = self.round_manager.get_round(round_number)

        if round_data is None:
            logger.error(f"Cannot record results: round {round_number} does not exist")
            return False

        success = self.result_recorder.record_round_results(
            round_data, results_data, self.players
        )

        if success:
            self.round_manager.mark_round_completed(round_number)
            logger.info(f"Recorded results for round {round_number}")

        return success

    # ========== Standings and Tiebreaks ==========

    def compute_tiebreakers(self) -> None:
        """Calculate tiebreak scores for all players."""
        self.tiebreak_calculator.calculate_all_tiebreaks(self.players)

    def get_standings(self) -> List[Player]:
        """Get current tournament standings.

        Returns:
            List of players sorted by rank (best to worst)
        """
        active_players = self.get_player_list(active_only=True)

        if not active_players:
            return []

        # Calculate tiebreaks
        self.compute_tiebreakers()

        # Sort by score and tiebreaks
        sorted_players = sorted(
            active_players,
            key=functools.cmp_to_key(self._compare_players),
            reverse=True,
        )

        return sorted_players

    def _compare_players(self, p1: Player, p2: Player) -> int:
        """Compare two players for standings order.

        Returns:
            1 if p1 ranks higher, -1 if p2 ranks higher, 0 if equal
        """
        # Compare scores
        if p1.score != p2.score:
            return 1 if p1.score > p2.score else -1

        # Check head-to-head if they've played
        p1_won, p2_won = self.tiebreak_calculator.calculate_head_to_head(p1, p2)
        if p1_won and not p2_won:
            return 1
        if p2_won and not p1_won:
            return -1

        # Compare tiebreaks in order
        for tb_key in self.config.tiebreak_order:
            tb1 = p1.tiebreakers.get(tb_key, 0.0)
            tb2 = p2.tiebreakers.get(tb_key, 0.0)
            if tb1 != tb2:
                return 1 if tb1 > tb2 else -1

        # Compare rating
        if hasattr(p1, "rating") and hasattr(p2, "rating"):
            if p1.rating != p2.rating:
                return 1 if p1.rating > p2.rating else -1

        # Compare name (alphabetically)
        if p1.name != p2.name:
            return -1 if p1.name < p2.name else 1

        return 0

    # ========== Utility Methods ==========

    def get_completed_rounds(self) -> int:
        """Get number of completed rounds.

        Returns:
            Count of completed rounds
        """
        return self.round_manager.completed_rounds_count

    def _get_eligible_bye_player(
        self, potential_bye_players: List[Player]
    ) -> Optional[Player]:
        """Determine the bye player according to Swiss rules.

        Priority:
        1. Active player who hasn't received a bye
        2. Lowest score, then lowest rating
        3. If all have had bye, assign second bye to lowest score/rating

        Args:
            potential_bye_players: List of players who could receive bye

        Returns:
            The player who should receive the bye
        """
        if not potential_bye_players:
            return None

        active_players = [p for p in potential_bye_players if p.is_active]
        if not active_players:
            return None

        # Find players without a bye
        no_bye_players = [p for p in active_players if not p.has_received_bye]

        if no_bye_players:
            # Give bye to player without one, lowest score/rating first
            no_bye_players.sort(
                key=lambda p: (
                    p.score,
                    getattr(p, "rating", 0),
                    p.name,
                )
            )
            selected = no_bye_players[0]
            logger.info(
                f"Assigning first bye to: {selected.name} "
                f"(Score: {selected.score}, Rating: {getattr(selected, 'rating', 0)})"
            )
            return selected
        else:
            # All have had a bye, assign second bye as last resort
            logger.warning(
                "All potential bye candidates have already received a bye. "
                "Assigning second bye as last resort."
            )
            active_players.sort(
                key=lambda p: (
                    p.score,
                    getattr(p, "rating", 0),
                    p.name,
                )
            )
            selected = active_players[0]
            logger.info(
                f"Assigning second bye to: {selected.name} "
                f"(Score: {selected.score}, Rating: {getattr(selected, 'rating', 0)})"
            )
            return selected

    # ========== Serialization ==========

    def to_dict(self) -> Dict[str, Any]:
        """Serialize tournament to dictionary.

        Returns:
            Dictionary containing all tournament data
        """
        return {
            "config": self.config.to_dict(),
            "players": [p.to_dict() for p in self.players.values()],
            "pairing_history": self.pairing_history.to_dict(),
            "rounds": [r.to_dict() for r in self.round_manager.rounds],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Tournament":
        """Deserialize tournament from dictionary.

        Args:
            data: Dictionary containing tournament data

        Returns:
            Reconstructed Tournament object
        """
        # Load config
        config = TournamentConfig.from_dict(data.get("config", data))

        # Load players
        players = [Player.from_dict(p_data) for p_data in data["players"]]

        # Create tournament
        tournament = cls(
            name=config.name,
            players=players,
            num_rounds=config.num_rounds,
            tiebreak_order=config.tiebreak_order,
            pairing_system=config.pairing_system,
        )

        # Load pairing history
        if "pairing_history" in data:
            tournament.pairing_history = PairingHistory.from_dict(
                data["pairing_history"]
            )

        # Load rounds
        if "rounds" in data:
            tournament.round_manager.rounds = [
                RoundData.from_dict(r) for r in data["rounds"]
            ]

        # Clear player caches
        for player in tournament.players.values():
            player._opponents_played_cache = []

        logger.info(f"Loaded tournament: {tournament.name}")
        return tournament
