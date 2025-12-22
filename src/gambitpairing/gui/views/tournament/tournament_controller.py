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

"""
Tournament business logic controller.

This module separates the tournament management business logic from the UI.
The TournamentController handles:
- Round preparation and pairing generation
- Result recording and validation
- Undo operations
- Player validation
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple

from gambitpairing.constants import (
    BYE_SCORE,
    DRAW_SCORE,
    LOSS_SCORE,
    RESULT_BLACK_WIN,
    RESULT_DRAW,
    RESULT_WHITE_WIN,
    WIN_SCORE,
)
from gambitpairing.utils import setup_logger

if TYPE_CHECKING:
    from gambitpairing.player import Player
    from gambitpairing.tournament import Tournament

logger = setup_logger(__name__)


@dataclass
class PairingGenerationResult:
    """Result of a pairing generation operation."""

    success: bool
    pairings: List[Tuple["Player", "Player"]]
    bye_player: Optional["Player"]
    error_message: Optional[str] = None


@dataclass
class ResultRecordingResult:
    """Result of a result recording operation."""

    success: bool
    error_message: Optional[str] = None
    tournament_finished: bool = False


@dataclass
class ValidationResult:
    """Result of a validation check."""

    valid: bool
    error_message: Optional[str] = None
    needs_confirmation: bool = False
    confirmation_message: Optional[str] = None


class TournamentController:
    """
    Controller for tournament business logic.

    This class encapsulates all tournament management logic, separating
    it from the UI layer. It provides a clean interface for:
    - Starting tournaments
    - Generating pairings for each round
    - Recording results
    - Undoing operations
    - Validating tournament state

    The controller does not directly interact with Qt widgets - it returns
    result objects that the UI layer can interpret.

    Parameters
    ----------
    tournament : Tournament
        The tournament object to manage
    """

    def __init__(self, tournament: Optional["Tournament"] = None):
        self.tournament = tournament
        self.current_round_index = 0
        self.last_recorded_results_data: List[Tuple[str, str, float]] = []

    def set_tournament(self, tournament: Optional["Tournament"]):
        """Set the tournament to manage."""
        self.tournament = tournament
        if tournament is None:
            self.current_round_index = 0
            self.last_recorded_results_data = []

    def set_current_round_index(self, idx: int):
        """Set the current round index."""
        self.current_round_index = idx

    def validate_minimum_players(
        self, for_preparation: bool = False
    ) -> ValidationResult:
        """
        Validate that there are enough players to proceed.

        Parameters
        ----------
        for_preparation : bool
            If True, only count active players (for mid-tournament rounds)
            If False, count all players (for tournament start)

        Returns
        -------
        ValidationResult
            Contains validation status and any error or confirmation messages
        """
        if not self.tournament:
            return ValidationResult(valid=False, error_message="No tournament loaded.")

        pairing_system = getattr(self.tournament, "pairing_system", "dutch_swiss")

        if for_preparation:
            players = [
                p
                for p in self.tournament.players.values()
                if getattr(p, "is_active", True)
            ]
        else:
            players = list(self.tournament.players.values())

        num_players = len(players)
        min_players = 2**self.tournament.num_rounds
        player_type = "active " if for_preparation else ""

        if pairing_system == "round_robin":
            if num_players < 3:
                return ValidationResult(
                    valid=False,
                    error_message=f"Round Robin tournaments require at least three {player_type}players.",
                )
        elif pairing_system == "dutch_swiss":
            if num_players < 2:
                return ValidationResult(
                    valid=False,
                    error_message=f"FIDE Dutch Swiss tournaments require at least two {player_type}players.",
                )
            if num_players < min_players:
                return ValidationResult(
                    valid=True,  # Can proceed with confirmation
                    needs_confirmation=True,
                    confirmation_message=(
                        f"For a {self.tournament.num_rounds}-round FIDE Dutch Swiss tournament, "
                        f"a minimum of {min_players} players is recommended. "
                        f"The tournament may not work properly. Do you want to continue anyway?"
                    ),
                )
        elif pairing_system == "manual":
            if num_players < 2:
                return ValidationResult(
                    valid=False,
                    error_message=f"Manual pairing tournaments require at least two {player_type}players.",
                )

        return ValidationResult(valid=True)

    def generate_pairings(
        self,
        round_index: int,
        allow_repeat_callback: Optional[Callable[["Player", "Player"], bool]] = None,
    ) -> PairingGenerationResult:
        """
        Generate pairings for a specific round.

        Parameters
        ----------
        round_index : int
            The 0-based round index to generate pairings for
        allow_repeat_callback : callable, optional
            Callback function to ask user about repeat pairings

        Returns
        -------
        PairingGenerationResult
            Contains success status, pairings, bye player, and any error message
        """
        if not self.tournament:
            return PairingGenerationResult(
                success=False,
                pairings=[],
                bye_player=None,
                error_message="No tournament loaded.",
            )

        if round_index >= self.tournament.num_rounds:
            return PairingGenerationResult(
                success=False,
                pairings=[],
                bye_player=None,
                error_message="All tournament rounds have been generated.",
            )

        display_round_number = round_index + 1

        try:
            pairings, bye_player = self.tournament.create_pairings(
                display_round_number,
                allow_repeat_pairing_callback=allow_repeat_callback,
            )

            # Validate pairings
            active_players = self.tournament._get_active_players()
            if not pairings and len(active_players) > 1 and not bye_player:
                if len(active_players) % 2 == 0:
                    return PairingGenerationResult(
                        success=False,
                        pairings=[],
                        bye_player=None,
                        error_message=(
                            f"Pairing generation failed for Round {display_round_number}. "
                            f"No pairings returned. Check logs and player statuses."
                        ),
                    )

            return PairingGenerationResult(
                success=True,
                pairings=pairings,
                bye_player=bye_player,
            )

        except Exception as e:
            logger.exception(
                f"Error generating pairings for Round {display_round_number}:"
            )
            return PairingGenerationResult(
                success=False,
                pairings=[],
                bye_player=None,
                error_message=f"Pairing generation failed: {e}",
            )

    def pairings_exist_for_round(self, round_index: int) -> bool:
        """Check if pairings already exist for a given round."""
        if not self.tournament:
            return False
        return round_index < len(self.tournament.rounds_pairings_ids)

    def clear_round_pairings(self, round_index: int):
        """Clear pairings for a round and all subsequent rounds."""
        if not self.tournament:
            return
        self.tournament.rounds_pairings_ids = self.tournament.rounds_pairings_ids[
            :round_index
        ]
        self.tournament.rounds_byes_ids = self.tournament.rounds_byes_ids[:round_index]

    def get_round_pairings(
        self, round_index: int
    ) -> Tuple[List[Tuple["Player", "Player"]], Optional["Player"]]:
        """
        Get the pairings and bye player for a specific round.

        Returns
        -------
        tuple
            (list of (white, black) tuples, bye_player or None)
        """
        if not self.tournament or round_index >= len(
            self.tournament.rounds_pairings_ids
        ):
            return [], None

        pairings_ids = self.tournament.rounds_pairings_ids[round_index]
        bye_id = self.tournament.rounds_byes_ids[round_index]

        pairings = []
        for w_id, b_id in pairings_ids:
            w = self.tournament.players.get(w_id)
            b = self.tournament.players.get(b_id)
            if w and b:
                pairings.append((w, b))

        bye_player = self.tournament.players.get(bye_id) if bye_id else None
        return pairings, bye_player

    def record_results(
        self, round_index: int, results_data: List[Tuple[str, str, float]]
    ) -> ResultRecordingResult:
        """
        Record results for a round.

        Parameters
        ----------
        round_index : int
            The 0-based round index
        results_data : list
            List of (white_id, black_id, white_score) tuples

        Returns
        -------
        ResultRecordingResult
            Contains success status and tournament completion state
        """
        if not self.tournament:
            return ResultRecordingResult(
                success=False, error_message="No tournament loaded."
            )

        if round_index >= len(self.tournament.rounds_pairings_ids):
            return ResultRecordingResult(
                success=False,
                error_message="No pairings available to record results for this round.",
            )

        try:
            if self.tournament.record_results(round_index, results_data):
                self.last_recorded_results_data = list(results_data)
                self.current_round_index = round_index + 1

                tournament_finished = (
                    self.current_round_index >= self.tournament.num_rounds
                )
                return ResultRecordingResult(
                    success=True, tournament_finished=tournament_finished
                )
            else:
                return ResultRecordingResult(
                    success=False,
                    error_message="Some results may not have been recorded properly.",
                )
        except Exception as e:
            logger.exception(f"Error recording results for round {round_index + 1}:")
            return ResultRecordingResult(
                success=False, error_message=f"Recording results failed: {e}"
            )

    def parse_result_to_score(self, result_const: str) -> Optional[float]:
        """
        Convert a result constant to a white score.

        Parameters
        ----------
        result_const : str
            One of RESULT_WHITE_WIN, RESULT_DRAW, RESULT_BLACK_WIN

        Returns
        -------
        float or None
            The white player's score (1.0, 0.5, or 0.0), or None if invalid
        """
        if result_const == RESULT_WHITE_WIN:
            return WIN_SCORE
        elif result_const == RESULT_DRAW:
            return DRAW_SCORE
        elif result_const == RESULT_BLACK_WIN:
            return LOSS_SCORE
        return None

    def can_undo(self) -> bool:
        """Check if undo is possible."""
        return (
            self.tournament is not None
            and len(self.last_recorded_results_data) > 0
            and self.current_round_index > 0
        )

    def undo_last_results(self) -> Tuple[bool, Optional[str]]:
        """
        Undo the last recorded round's results.

        Returns
        -------
        tuple
            (success: bool, error_message: str or None)
        """
        if not self.can_undo():
            return False, "No results from a completed round are available to undo."

        try:
            round_index_being_undone = self.current_round_index - 1

            # Revert player stats for each game
            for white_id, black_id, _ in self.last_recorded_results_data:
                p_white = self.tournament.players.get(white_id)
                p_black = self.tournament.players.get(black_id)
                if p_white:
                    self._revert_player_round_data(p_white)
                if p_black:
                    self._revert_player_round_data(p_black)

            # Revert bye player stats
            if round_index_being_undone < len(self.tournament.rounds_byes_ids):
                bye_player_id = self.tournament.rounds_byes_ids[
                    round_index_being_undone
                ]
                if bye_player_id:
                    p_bye = self.tournament.players.get(bye_player_id)
                    if p_bye:
                        self._revert_player_round_data(p_bye)

            # Log warning about manual pairings
            if round_index_being_undone in self.tournament.manual_pairings:
                logger.warning(
                    f"Manual pairings for round {round_index_being_undone + 1} "
                    f"were part of its setup and are not automatically reverted."
                )

            self.last_recorded_results_data = []
            self.current_round_index -= 1

            return True, None

        except Exception as e:
            logger.exception("Error undoing results:")
            return False, f"Undoing results failed: {e}"

    def _revert_player_round_data(self, player: "Player"):
        """
        Remove the last round's data from a player's history.

        Parameters
        ----------
        player : Player
            The player to revert
        """
        if not player.results:
            return

        last_result = player.results.pop()
        if last_result is not None:
            player.score = round(player.score - last_result, 1)

        if player.running_scores:
            player.running_scores.pop()

        last_opponent_id = player.opponent_ids.pop() if player.opponent_ids else None
        last_color = player.color_history.pop() if player.color_history else None

        if last_color == "Black":
            player.num_black_games = max(0, player.num_black_games - 1)

        if last_opponent_id is None:  # Was a bye
            player.has_received_bye = (
                (None in player.opponent_ids) if player.opponent_ids else False
            )
            logger.debug(
                f"Player {player.name} bye undone. Has received bye: {player.has_received_bye}"
            )

        # Invalidate opponent cache
        player._opponents_played_cache = []

    def set_manual_pairings(
        self,
        round_index: int,
        pairings: List[Tuple["Player", "Player"]],
        bye_player: Optional["Player"],
    ) -> bool:
        """
        Set manual pairings for a round.

        Parameters
        ----------
        round_index : int
            The 0-based round index
        pairings : list
            List of (white, black) player tuples
        bye_player : Player or None
            The player receiving a bye

        Returns
        -------
        bool
            True if successful
        """
        if not self.tournament:
            return False
        return self.tournament.set_manual_pairings(round_index, pairings, bye_player)

    def get_active_players(self) -> List["Player"]:
        """Get list of active players in the tournament."""
        if not self.tournament:
            return []
        return [p for p in self.tournament.players.values() if p.is_active]

    def is_manual_pairing_system(self) -> bool:
        """Check if the tournament uses manual pairing."""
        if not self.tournament:
            return False
        return self.tournament.pairing_system == "manual"

    def format_results_for_log(
        self, results_data: List[Tuple[str, str, float]], round_index: int
    ) -> List[str]:
        """
        Format results data for logging/history.

        Parameters
        ----------
        results_data : list
            List of (white_id, black_id, white_score) tuples
        round_index : int
            The round index these results are for

        Returns
        -------
        list of str
            Formatted log messages
        """
        if not self.tournament:
            return []

        messages = []

        # Log paired game results
        for w_id, b_id, score_w in results_data:
            w = self.tournament.players.get(w_id)
            b = self.tournament.players.get(b_id)
            score_b_display = f"{WIN_SCORE - score_w:.1f}"
            w_name = w.name if w else w_id
            b_name = b.name if b else b_id
            messages.append(
                f"  {w_name} ({score_w:.1f}) - {b_name} ({score_b_display})"
            )

        # Log bye
        if round_index < len(self.tournament.rounds_byes_ids):
            bye_id = self.tournament.rounds_byes_ids[round_index]
            if bye_id:
                bye_player = self.tournament.players.get(bye_id)
                if bye_player:
                    status = (
                        " (Inactive - No Score)" if not bye_player.is_active else ""
                    )
                    bye_score = BYE_SCORE if bye_player.is_active else 0.0
                    messages.append(
                        f"  Bye point ({bye_score:.1f}) awarded to: {bye_player.name}{status}"
                    )
                else:
                    messages.append(f"  Bye player ID {bye_id} not found (error).")

        return messages
