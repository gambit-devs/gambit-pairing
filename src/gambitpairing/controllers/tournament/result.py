"""Result recording and validation for tournaments.

This module handles recording match results with proper validation and error checking.
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

from typing import Dict, List, Tuple

from gambitpairing.constants import BYE_SCORE, WIN_SCORE
from gambitpairing.models.player import Player
from gambitpairing.models.tournament import MatchResult, RoundData
from gambitpairing.models.enums import Colour
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


class ResultRecorder:
    """Handles recording and validating match results.

    This class is responsible for:
    - Recording match results with proper validation
    - Updating player statistics
    - Handling bye results
    - Preventing duplicate result recording
    """

    def record_round_results(
        self,
        round_data: RoundData,
        results_data: List[Tuple[str, str, float]],
        players: Dict[str, Player],
    ) -> bool:
        """Record results for all matches in a round.

        Args:
            round_data: The round data to record results for
            results_data: List of (white_id, black_id, white_score) tuples
            players: Dictionary of all players (id -> Player)

        Returns:
            True if all results recorded successfully, False if any errors occurred
        """
        if round_data.is_completed:
            logger.warning(
                f"Round {round_data.round_number} is already completed, "
                "results may be overwritten"
            )

        round_number = round_data.round_number
        pairing_ids = {(w, b) for w, b in round_data.pairings}
        processed_pairs = set()
        success = True

        # Record game results
        for white_id, black_id, white_score in results_data:
            if not self._validate_result_entry(
                white_id, black_id, white_score, pairing_ids, processed_pairs, players
            ):
                success = False
                continue

            if not self._record_game_result(
                white_id, black_id, white_score, round_number, round_data, players
            ):
                success = False
                continue

            processed_pairs.add((white_id, black_id))

        # Record bye result
        if round_data.bye_player_id:
            if not self._record_bye_result(
                round_data.bye_player_id, round_number, players
            ):
                success = False

        # Check for unprocessed pairings
        expected_pairs = pairing_ids.copy()
        unprocessed = expected_pairs - processed_pairs
        if unprocessed:
            logger.warning(
                f"Round {round_number}: Some pairings were not processed: {unprocessed}"
            )

        return success

    def _validate_result_entry(
        self,
        white_id: str,
        black_id: str,
        white_score: float,
        pairing_ids: set,
        processed_pairs: set,
        players: Dict[str, Player],
    ) -> bool:
        """Validate a result entry before recording.

        Returns:
            True if valid, False otherwise
        """
        # Check if players exist
        white = players.get(white_id)
        black = players.get(black_id)

        if not white or not black:
            logger.error(f"Cannot find players: {white_id} and/or {black_id}")
            return False

        # Check if this pairing exists in the round
        if (white_id, black_id) not in pairing_ids:
            logger.error(
                f"Pairing ({white.name}, {black.name}) not found in round pairings"
            )
            return False

        # Check for duplicate recording
        if (white_id, black_id) in processed_pairs:
            logger.warning(
                f"Result for {white.name} vs {black.name} already recorded in this batch"
            )
            return False

        # Validate score
        if not (0.0 <= white_score <= 1.0):
            logger.error(f"Invalid score: {white_score} (must be between 0.0 and 1.0)")
            return False

        return True

    def _record_game_result(
        self,
        white_id: str,
        black_id: str,
        white_score: float,
        round_number: int,
        round_data: RoundData,
        players: Dict[str, Player],
    ) -> bool:
        """Record the result of a single game.

        Returns:
            True if successful, False otherwise
        """
        white = players[white_id]
        black = players[black_id]
        black_score = WIN_SCORE - white_score

        # Add result to round data
        match_result = MatchResult(
            white_id=white_id, black_id=black_id, white_score=white_score
        )
        round_data.results.append(match_result)

        # Update player records
        white.add_round_result(opponent=black, result=white_score, color=Colour.WHITE)
        black.add_round_result(opponent=white, result=black_score, color=Colour.BLACK)

        logger.debug(
            f"Recorded: {white.name} ({white_score}) vs {black.name} ({black_score})"
        )
        return True

    def _record_bye_result(
        self, bye_player_id: str, round_number: int, players: Dict[str, Player]
    ) -> bool:
        """Record a bye result for a player.

        Returns:
            True if successful, False otherwise
        """
        bye_player = players.get(bye_player_id)
        if not bye_player:
            logger.error(f"Cannot find bye player: {bye_player_id}")
            return False

        # Check if bye already recorded
        if len(bye_player.results) >= round_number:
            logger.warning(
                f"Bye for {bye_player.name} in round {round_number} "
                "appears to already be recorded"
            )
            return True  # Not necessarily an error

        # Record bye - active players get the bye score, inactive get 0
        bye_score = BYE_SCORE if bye_player.is_active else 0.0
        bye_player.add_round_result(opponent=None, result=bye_score, color=None)

        logger.debug(
            f"Recorded bye for {bye_player.name} "
            f"(score: {bye_score}, active: {bye_player.is_active})"
        )
        return True

    def undo_round_results(
        self, round_data: RoundData, players: Dict[str, Player]
    ) -> bool:
        """Undo results for a round by removing them from player records.

        Args:
            round_data: The round data to undo
            players: Dictionary of all players

        Returns:
            True if successful, False otherwise
        """
        if not round_data.is_completed:
            logger.warning(
                f"Round {round_data.round_number} is not completed, nothing to undo"
            )
            return False

        round_number = round_data.round_number
        success = True

        # Undo game results
        for match_result in round_data.results:
            white = players.get(match_result.white_id)
            black = players.get(match_result.black_id)

            if white and black:
                if not self._undo_player_result(white, round_number):
                    success = False
                if not self._undo_player_result(black, round_number):
                    success = False

        # Undo bye result
        if round_data.bye_player_id:
            bye_player = players.get(round_data.bye_player_id)
            if bye_player:
                if not self._undo_player_result(bye_player, round_number):
                    success = False

        # Clear results from round data
        round_data.results.clear()
        round_data.is_completed = False

        logger.info(f"Undid results for round {round_number}")
        return success

    def _undo_player_result(self, player: Player, round_number: int) -> bool:
        """Undo a single player's result for a round.

        Returns:
            True if successful, False otherwise
        """
        # Check if player has a result for this round
        if len(player.results) < round_number:
            logger.warning(
                f"Cannot undo: {player.name} has no result for round {round_number}"
            )
            return False

        # Remove the last result (should be for this round)
        if len(player.results) >= round_number:
            removed_result = player.results.pop()
            player.score -= removed_result
            player.opponent_ids.pop()
            player.color_history.pop()

            if player.running_scores:
                player.running_scores.pop()

            # Update black game count if needed
            if player.color_history and player.color_history[-1] == Colour.BLACK:
                player.num_black_games = max(0, player.num_black_games - 1)

            # Update bye status if this was a bye
            if player.opponent_ids and player.opponent_ids[-1] is None:
                # Check if player has any other byes
                player.has_received_bye = None in player.opponent_ids

            logger.debug(f"Undid result for {player.name} in round {round_number}")
            return True

        return False
