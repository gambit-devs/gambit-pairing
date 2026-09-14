"""
Tournament business logic controller.

This module separates the tournament management business logic
The TournamentController handles:
- Round preparation and pairing generation
- Result recording and validation
- Undo operations
- Player validation
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
from gambitpairing.models.pairing import (
    PairingGenerationResult,
    RecordingResult,
    ValidationResult,
)
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)

if TYPE_CHECKING:
    from gambitpairing.controllers.tournament.session import (
        TournamentSession as Tournament,
    )
    from gambitpairing.models.player import Player


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
        self.current_round_index = (
            tournament.get_completed_rounds() if tournament else 0
        )
        self.last_recorded_results_data: List[tuple] = []

    def set_tournament(self, tournament: Optional["Tournament"]):
        """Set the tournament to manage."""
        self.tournament = tournament
        self.current_round_index = (
            tournament.get_completed_rounds() if tournament else 0
        )
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
        player_type = "active " if for_preparation else ""

        if pairing_system == "round_robin":
            if num_players < 3:
                return ValidationResult(
                    valid=False,
                    error_message=f"Round Robin tournaments require at least three {player_type}players.",
                )
        elif pairing_system in {"bbp_dutch", "dutch_swiss"}:
            min_players = 2**self.tournament.num_rounds
            if num_players < 2:
                return ValidationResult(
                    valid=False,
                    error_message=f"Dutch Swiss tournaments require at least two {player_type}players.",
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

        if pairing_system in {"round_robin", "bbp_dutch", "dutch_swiss", "manual"}:
            return ValidationResult(valid=True)
        return ValidationResult(
            valid=False,
            error_message=f"pairing system {pairing_system} not handled correctly.",
        )

    def generate_pairings(
        self,
        round_index: int,
        allow_repeat_callback: Optional[Callable[[Player, Player], bool]] = None,
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
            from copy import deepcopy

            from .pairing_job import commit_pairing_document

            expected = self.tournament.to_dict()
            prepared = deepcopy(self.tournament)
            if round_index != prepared.get_completed_rounds():
                raise ValueError("Only the next uncompleted round can be paired")
            prepared.clear_rounds_from(round_index)
            prepared.create_pairings(
                display_round_number,
                allow_repeat_pairing_callback=allow_repeat_callback,
            )
            commit_pairing_document(
                self.tournament,
                expected,
                {
                    "document": prepared.to_dict(),
                    "engine": prepared.round_controller.last_engine,
                },
            )
            pairings, bye_player = self.tournament.get_pairings_for_round(round_index)

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
        return self.get_round_data(round_index) is not None

    def get_round_data(self, round_index: int):
        """Return the model data for a zero-based round index."""
        if not self.tournament or round_index < 0:
            return None
        return self.tournament.round_controller.get_round(round_index + 1)

    @property
    def generated_round_count(self) -> int:
        """Return the number of rounds currently represented by the model."""
        if not self.tournament:
            return 0
        return len(self.tournament.round_controller.rounds)

    def get_round_results(self, round_index: int, pending: bool = False) -> list:
        """Return pending or finalized results for a round without exposing storage."""
        round_data = self.get_round_data(round_index)
        if round_data is None:
            return []
        return list(round_data.pending_results if pending else round_data.results)

    def set_pending_results(self, round_index: int, results_data: List[tuple]) -> bool:
        """Persist in-progress result entry without changing standings."""
        round_data = self.get_round_data(round_index)
        if not self.tournament or round_data is None or round_data.is_completed:
            return False
        return self.tournament.result_recorder.set_pending_results(
            round_data, results_data
        )

    def clear_round_pairings(self, round_index: int):
        """Clear pairings for a round and all subsequent rounds."""
        if not self.tournament:
            return
        self.tournament.clear_rounds_from(round_index)

    def get_round_pairings(
        self, round_index: int
    ) -> Tuple[List[Tuple[Player, Player]], Optional[Player]]:
        """
        Get the pairings and bye player for a specific round.

        Returns
        -------
        tuple
            (list of (white, black) tuples, bye_player or None)
        """
        round_data = self.get_round_data(round_index)
        if not self.tournament or round_data is None:
            return [], None

        pairings = []
        for w_id, b_id in round_data.pairings:
            w = self.tournament.players.get(w_id)
            b = self.tournament.players.get(b_id)
            if w and b:
                pairings.append((w, b))

        bye_player = (
            self.tournament.players.get(round_data.bye_player_id)
            if round_data.bye_player_id
            else None
        )
        return pairings, bye_player

    def record_results(
        self, round_index: int, results_data: List[tuple]
    ) -> RecordingResult:
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
            return RecordingResult(success=False, error_message="No tournament loaded.")

        if round_index >= len(self.tournament.rounds_pairings_ids):
            return RecordingResult(
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
                return RecordingResult(
                    success=True, tournament_finished=tournament_finished
                )
            else:
                return RecordingResult(
                    success=False,
                    error_message="Some results may not have been recorded properly.",
                )
        except Exception as e:
            logger.exception(f"Error recording results for round {round_index + 1}:")
            return RecordingResult(
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
        if self.tournament is None or self.current_round_index <= 0:
            return False
        round_data = self.get_round_data(self.current_round_index - 1)
        return bool(
            self.last_recorded_results_data
            or (round_data is not None and round_data.is_completed)
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
            round_data = self.get_round_data(round_index_being_undone)
            if round_data is None:
                return False, "The completed round could not be found."

            # ResultRecorder owns the player-history invariants. Keeping the
            # mutation there prevents the view from having to know how scores,
            # colors, byes, and match history are represented.
            if not self.tournament.result_recorder.undo_round_results(
                round_data, self.tournament.players
            ):
                return False, "The completed round could not be undone."
            round_data.pending_results.clear()
            self.tournament.clear_rounds_from(round_index_being_undone + 1)

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
        pairings: List[Tuple[Player, Player]],
        bye_player: Optional[Player],
        bye_type: str = "full",
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
        return self.tournament.set_manual_pairings(
            round_index, pairings, bye_player, bye_type
        )

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

    def _format_results_for_log(
        self, results_data: List[tuple], round_index: int
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
        for result_entry in results_data:
            w_id, b_id, score_w = result_entry[:3]
            score_b = result_entry[3] if len(result_entry) > 3 else WIN_SCORE - score_w
            w = self.tournament.players.get(w_id)
            b = self.tournament.players.get(b_id)
            w_name = w.name if w else w_id
            b_name = b.name if b else b_id
            messages.append(f"  {w_name} ({score_w:.1f}) - {b_name} ({score_b:.1f})")

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


#  LocalWords:  ValidationResult PairingGenerationResult
