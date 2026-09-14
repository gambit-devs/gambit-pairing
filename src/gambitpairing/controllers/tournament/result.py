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

from copy import deepcopy
import math
from numbers import Real
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple

from gambitpairing.constants import (
    BYE_SCORE,
    DRAW_SCORE,
    FULL_POINT_BYE_SCORE,
    HALF_POINT_BYE_SCORE,
    LOSS_SCORE,
    OUTCOME_BYE,
    OUTCOME_DOUBLE_FORFEIT,
    OUTCOME_FORFEIT_LOSS,
    OUTCOME_FORFEIT_WIN,
    OUTCOME_NORMAL_GAME,
    WIN_SCORE,
    ZERO_POINT_BYE_SCORE,
)
from gambitpairing.models.enums import Colour
from gambitpairing.models.player import Player
from gambitpairing.models.tournament import MatchResult, RoundData
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)

VALID_GAME_OUTCOMES = {
    OUTCOME_NORMAL_GAME,
    OUTCOME_FORFEIT_WIN,
    OUTCOME_FORFEIT_LOSS,
    OUTCOME_DOUBLE_FORFEIT,
}
VALID_GAME_SCORES = {LOSS_SCORE, DRAW_SCORE, WIN_SCORE}
SCORE_TOLERANCE = 1e-9


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
        results_data: List[tuple],
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
            logger.warning("Round %s is already completed", round_data.round_number)
            return False
        if not isinstance(round_data.results, list) or not isinstance(
            round_data.pending_results, list
        ):
            logger.error("Round %s has invalid result storage", round_data.round_number)
            return False
        if round_data.results:
            logger.warning(
                "Round %s already contains finalized results",
                round_data.round_number,
            )
            return False

        expected_pairs = self._validate_round_pairings(round_data, players)
        if expected_pairs is None:
            return False

        prepared_results = self._prepare_results(
            results_data,
            round_data,
            players,
            expected_pairs,
            require_complete=True,
        )
        if prepared_results is None:
            return False

        affected_ids = {
            player_id
            for result in prepared_results
            for player_id in (result.white_id, result.black_id)
        }
        if round_data.bye_player_id:
            affected_ids.add(round_data.bye_player_id)

        snapshots: Dict[str, Dict[str, Any]] = {
            player_id: deepcopy(dict(players[player_id].__dict__))
            for player_id in players
        }
        original_results = deepcopy(round_data.results)
        original_pending_results = deepcopy(round_data.pending_results)
        original_bye_type = round_data.bye_type

        try:
            for player in players.values():
                self._pad_skipped_rounds(player, round_data.round_number - 1)
            for result in prepared_results:
                if not self._record_game_result(result, round_data, players):
                    raise ValueError("Unable to record a validated game result")

            if round_data.bye_player_id and not self._record_bye_result(
                round_data.bye_player_id,
                round_data.round_number,
                players,
                getattr(round_data, "bye_type", "full"),
            ):
                raise ValueError("Unable to record the round bye")

            round_data.pending_results.clear()
            if (
                round_data.bye_player_id
                and not players[round_data.bye_player_id].is_active
            ):
                round_data.bye_type = "zero"
            for player_id, player in players.items():
                if player_id not in affected_ids:
                    self._pad_skipped_rounds(player, round_data.round_number)
        except Exception:
            self._restore_player_snapshots(players, snapshots)
            round_data.results[:] = original_results
            round_data.pending_results[:] = original_pending_results
            round_data.bye_type = original_bye_type
            logger.exception(
                "Failed to record results for round %s; state was restored",
                round_data.round_number,
            )
            return False

        return True

    @staticmethod
    def _pad_skipped_rounds(player: Player, round_number: int) -> None:
        while len(player.results) < round_number:
            player.results.append(None)
            player.opponent_ids.append(None)
            player.outcome_types.append(None)
            player.color_history.append(None)
            player.running_scores.append(player.score)
            player.match_history.append(None)

    def set_pending_results(
        self,
        round_data: RoundData,
        results_data: List[tuple],
    ) -> bool:
        """Store result-entry progress without applying player scores.

        The Rounds workspace is intentionally allowed to autosave partially
        entered rows. Pending results use the same ``MatchResult`` shape as
        finalized results, but remain outside ``round_data.results`` until
        ``record_round_results`` succeeds.
        """
        if round_data.is_completed:
            return False

        pairing_structure = self._pairing_structure(round_data.pairings)
        if pairing_structure is None:
            logger.error("Round %s has invalid pairings", round_data.round_number)
            return False
        _pairing_orientations, expected_pairs, _assigned_ids = pairing_structure
        prepared_results = self._prepare_results(
            results_data,
            round_data,
            players=None,
            expected_pairs=expected_pairs,
            require_complete=False,
        )
        if prepared_results is None:
            return False

        round_data.pending_results = prepared_results
        return True

    @staticmethod
    def _match_result_from_entry(result_entry: tuple) -> MatchResult:
        """Convert a UI/controller result tuple into a model result."""
        if (
            not isinstance(result_entry, (tuple, list))
            or not 3 <= len(result_entry) <= 5
        ):
            raise ValueError(
                "A result entry must contain between three and five values"
            )

        white_id, black_id, white_score = result_entry[:3]
        if not isinstance(white_id, str) or not isinstance(black_id, str):
            raise ValueError("Result player IDs must be strings")
        if not isinstance(white_score, Real) or isinstance(white_score, bool):
            raise ValueError("White score must be numeric")

        black_score_override = None
        outcome_type = OUTCOME_NORMAL_GAME
        if len(result_entry) > 3:
            fourth_value = result_entry[3]
            if isinstance(fourth_value, str):
                outcome_type = fourth_value
            elif isinstance(fourth_value, Real) and not isinstance(fourth_value, bool):
                black_score_override = float(fourth_value)
            else:
                raise ValueError("The fourth result value must be an outcome or score")
        if len(result_entry) > 4:
            if not isinstance(result_entry[4], str):
                raise ValueError("The fifth result value must be an outcome")
            outcome_type = result_entry[4]

        # Older callers represented a double forfeit as (0.0, 0.0).
        if (
            outcome_type == OUTCOME_NORMAL_GAME
            and black_score_override is not None
            and float(white_score) == LOSS_SCORE
            and black_score_override == LOSS_SCORE
        ):
            outcome_type = OUTCOME_DOUBLE_FORFEIT

        return MatchResult(
            white_id=white_id,
            black_id=black_id,
            white_score=float(white_score),
            black_score_override=black_score_override,
            outcome_type=outcome_type,
        )

    def _prepare_results(
        self,
        results_data: List[tuple],
        round_data: RoundData,
        players: Optional[Dict[str, Player]],
        expected_pairs: Set[frozenset],
        require_complete: bool,
    ) -> Optional[List[MatchResult]]:
        """Parse and validate a result batch without changing application state."""
        if not isinstance(results_data, (list, tuple)):
            logger.error("Results must be provided as a list or tuple")
            return None

        prepared: List[MatchResult] = []
        processed_pairs: Set[frozenset] = set()
        pairing_structure = self._pairing_structure(round_data.pairings)
        if pairing_structure is None:
            logger.error("Round %s has invalid pairings", round_data.round_number)
            return None
        pairing_orientations, round_pairs, _assigned_ids = pairing_structure
        if round_pairs != expected_pairs:
            logger.error(
                "Round %s pairing state changed during validation",
                round_data.round_number,
            )
            return None

        for result_entry in results_data:
            try:
                result = self._match_result_from_entry(result_entry)
            except (TypeError, ValueError, OverflowError) as error:
                logger.error("Invalid result entry: %s", error)
                return None

            if not self._validate_match_result(
                result,
                pairing_orientations,
                expected_pairs,
                processed_pairs,
                players,
            ):
                return None

            processed_pairs.add(frozenset((result.white_id, result.black_id)))
            prepared.append(result)

        if require_complete and processed_pairs != expected_pairs:
            missing = expected_pairs - processed_pairs
            logger.error(
                "Round %s is missing results for pairings: %s",
                round_data.round_number,
                missing,
            )
            return None

        return prepared

    def _validate_round_pairings(
        self, round_data: RoundData, players: Dict[str, Player]
    ) -> Optional[Set[frozenset]]:
        """Validate round structure before any player state is changed."""
        pairing_structure = self._pairing_structure(round_data.pairings)
        if pairing_structure is None:
            logger.error("Round %s has invalid pairings", round_data.round_number)
            return None

        pairing_orientations, expected_pairs, assigned_ids = pairing_structure
        for white_id, black_id in pairing_orientations:
            if white_id not in players or black_id not in players:
                logger.error(
                    "Round %s contains unknown pairing IDs",
                    round_data.round_number,
                )
                return None

        bye_player_id = round_data.bye_player_id
        if bye_player_id is not None:
            if not isinstance(bye_player_id, str) or bye_player_id not in players:
                logger.error(
                    "Round %s has an unknown bye player", round_data.round_number
                )
                return None
            if bye_player_id in assigned_ids:
                logger.error(
                    "Round %s assigns its bye player to a game", round_data.round_number
                )
                return None

        return expected_pairs

    @staticmethod
    def _pairing_structure(
        pairings: object,
    ) -> Optional[Tuple[Set[Tuple[str, str]], Set[frozenset], Set[str]]]:
        """Return validated pairing identities without requiring a player map."""
        if not isinstance(pairings, (list, tuple)):
            return None

        orientations: Set[Tuple[str, str]] = set()
        pairs: Set[frozenset] = set()
        assigned_ids: Set[str] = set()
        for pairing in pairings:
            if (
                not isinstance(pairing, (tuple, list))
                or len(pairing) != 2
                or not all(isinstance(player_id, str) for player_id in pairing)
            ):
                return None
            white_id, black_id = pairing
            pair = frozenset((white_id, black_id))
            if (
                not white_id
                or not black_id
                or white_id == black_id
                or pair in pairs
                or white_id in assigned_ids
                or black_id in assigned_ids
            ):
                return None
            orientations.add((white_id, black_id))
            pairs.add(pair)
            assigned_ids.update((white_id, black_id))

        return orientations, pairs, assigned_ids

    def _validate_match_result(
        self,
        result: MatchResult,
        pairing_orientations: Set[Tuple[str, str]],
        expected_pairs: Set[frozenset],
        processed_pairs: Set[frozenset],
        players: Optional[Dict[str, Player]],
    ) -> bool:
        """Validate result identity, outcome, and score invariants."""
        white_id = result.white_id
        black_id = result.black_id
        pair = frozenset((white_id, black_id))

        if players is not None and (white_id not in players or black_id not in players):
            logger.error("Cannot find players: %s and/or %s", white_id, black_id)
            return False
        if (white_id, black_id) not in pairing_orientations:
            logger.error("Pairing (%s, %s) is not in the round", white_id, black_id)
            return False
        if pair not in expected_pairs or pair in processed_pairs:
            logger.error(
                "Result for pairing (%s, %s) is duplicated or unexpected",
                white_id,
                black_id,
            )
            return False
        if result.outcome_type not in VALID_GAME_OUTCOMES:
            logger.error("Unknown result outcome: %s", result.outcome_type)
            return False
        if not self._is_valid_score(result.white_score):
            logger.error("Invalid white score: %s", result.white_score)
            return False

        if result.outcome_type == OUTCOME_DOUBLE_FORFEIT:
            if result.white_score != LOSS_SCORE or result.black_score != LOSS_SCORE:
                logger.error("Double forfeits must score zero for both players")
                return False
            return True

        if result.outcome_type in {OUTCOME_FORFEIT_WIN, OUTCOME_FORFEIT_LOSS}:
            if result.white_score not in {LOSS_SCORE, WIN_SCORE}:
                logger.error("Forfeit results must be decisive")
                return False

        if not self._is_valid_score(result.black_score):
            logger.error("Invalid black score: %s", result.black_score)
            return False
        if not math.isclose(
            result.white_score + result.black_score,
            WIN_SCORE,
            abs_tol=SCORE_TOLERANCE,
        ):
            logger.error("Game scores must sum to one point")
            return False
        return True

    @staticmethod
    def _is_valid_score(score: object) -> bool:
        return (
            isinstance(score, Real)
            and not isinstance(score, bool)
            and math.isfinite(float(score))
            and any(
                math.isclose(float(score), valid_score, abs_tol=SCORE_TOLERANCE)
                for valid_score in VALID_GAME_SCORES
            )
        )

    @staticmethod
    def _restore_player_snapshots(
        players: Dict[str, Player], snapshots: Mapping[str, Mapping[str, Any]]
    ) -> None:
        for player_id, state in snapshots.items():
            players[player_id].__dict__.clear()
            players[player_id].__dict__.update(deepcopy(dict(state)))
        for player_id in snapshots:
            players[player_id]._opponents_played_cache = []

    def _record_game_result(
        self,
        result: MatchResult,
        round_data: RoundData,
        players: Dict[str, Player],
    ) -> bool:
        """Record the result of a single game.

        Returns:
            True if successful, False otherwise
        """
        white = players[result.white_id]
        black = players[result.black_id]
        actual_black_score = result.black_score
        white_outcome, black_outcome = self._game_outcomes(
            result.outcome_type, result.white_score
        )
        white_score_before, black_score_before = white.score, black.score

        # Add result to round data
        match_result = MatchResult(
            white_id=result.white_id,
            black_id=result.black_id,
            white_score=result.white_score,
            black_score_override=result.black_score_override,
            outcome_type=result.outcome_type,
        )
        round_data.results.append(match_result)

        # Update player records
        white.add_round_result(
            opponent=black,
            result=result.white_score,
            color=Colour.WHITE,
            outcome_type=white_outcome,
            opponent_score_before=black_score_before,
        )
        black.add_round_result(
            opponent=white,
            result=actual_black_score,
            color=Colour.BLACK,
            outcome_type=black_outcome,
            opponent_score_before=white_score_before,
        )

        logger.debug(
            f"Recorded: {white.name} ({result.white_score}) vs "
            f"{black.name} ({actual_black_score})"
        )
        return True

    @staticmethod
    def _game_outcomes(outcome_type: str, white_score: float) -> Tuple[str, str]:
        if outcome_type in {OUTCOME_FORFEIT_WIN, OUTCOME_FORFEIT_LOSS}:
            if white_score == WIN_SCORE:
                return OUTCOME_FORFEIT_WIN, OUTCOME_FORFEIT_LOSS
            return OUTCOME_FORFEIT_LOSS, OUTCOME_FORFEIT_WIN
        return outcome_type, outcome_type

    def _record_bye_result(
        self,
        bye_player_id: str,
        round_number: int,
        players: Dict[str, Player],
        bye_type: str = "full",
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
            return False

        if not bye_player.is_active or bye_type == "zero":
            bye_score = ZERO_POINT_BYE_SCORE
        elif bye_type == "half":
            bye_score = HALF_POINT_BYE_SCORE
        elif bye_type == "full":
            bye_score = FULL_POINT_BYE_SCORE
        else:
            logger.warning(
                "Unknown bye type %r; using the configured full-point bye", bye_type
            )
            bye_score = BYE_SCORE
        bye_player.add_round_result(
            opponent=None,
            result=bye_score,
            color=None,
            outcome_type=OUTCOME_BYE,
        )

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

        if not isinstance(round_data.results, list) or not isinstance(
            round_data.pending_results, list
        ):
            logger.error("Round %s has invalid stored results", round_data.round_number)
            return False

        pairing_structure = self._pairing_structure(round_data.pairings)
        if pairing_structure is None:
            logger.error("Round %s has invalid pairings", round_data.round_number)
            return False
        pairing_orientations, expected_pairs, _assigned_ids = pairing_structure
        if self._validate_round_pairings(round_data, players) is None:
            return False
        processed_pairs: Set[frozenset] = set()
        for match_result in round_data.results:
            if not isinstance(match_result, MatchResult):
                logger.error(
                    "Round %s contains an invalid stored result",
                    round_data.round_number,
                )
                return False
            if not self._validate_match_result(
                match_result,
                pairing_orientations,
                expected_pairs,
                processed_pairs,
                players,
            ):
                logger.error(
                    "Round %s contains an invalid stored result",
                    round_data.round_number,
                )
                return False
            processed_pairs.add(
                frozenset((match_result.white_id, match_result.black_id))
            )
        if processed_pairs != expected_pairs:
            logger.error(
                "Round %s does not contain one result for every pairing",
                round_data.round_number,
            )
            return False

        operations: List[Tuple[Player, Optional[str], float, Optional[Colour], str]] = (
            []
        )
        affected_ids: Set[str] = set()

        for match_result in round_data.results:
            white = players.get(match_result.white_id)
            black = players.get(match_result.black_id)
            if white is None or black is None:
                logger.error("Cannot undo a result with unknown players")
                return False
            if white.id in affected_ids or black.id in affected_ids:
                logger.error(
                    "Round %s contains duplicate player results",
                    round_data.round_number,
                )
                return False

            white_outcome, black_outcome = self._game_outcomes(
                match_result.outcome_type, match_result.white_score
            )
            operations.extend(
                [
                    (
                        white,
                        black.id,
                        match_result.white_score,
                        Colour.WHITE,
                        white_outcome,
                    ),
                    (
                        black,
                        white.id,
                        match_result.black_score,
                        Colour.BLACK,
                        black_outcome,
                    ),
                ]
            )
            affected_ids.update((white.id, black.id))

        if round_data.bye_player_id:
            bye_player = players.get(round_data.bye_player_id)
            if bye_player is None or bye_player.id in affected_ids:
                logger.error("Cannot undo an invalid bye result")
                return False
            if not bye_player.results:
                logger.error("Cannot undo a bye without player history")
                return False
            raw_bye_score = bye_player.results[-1]
            if raw_bye_score is None:
                logger.error("Cannot undo a bye with an invalid player score")
                return False
            try:
                bye_score = float(raw_bye_score)
            except (TypeError, ValueError):
                logger.error("Cannot undo a bye with an invalid player score")
                return False
            operations.append((bye_player, None, bye_score, None, OUTCOME_BYE))
            affected_ids.add(bye_player.id)

        if not operations:
            logger.error("Round %s has no results to undo", round_data.round_number)
            return False

        for player, opponent_id, score, color, outcome_type in operations:
            if not self._history_matches(
                player, opponent_id, score, color, outcome_type
            ):
                logger.error(
                    "Latest history for %s does not match round %s",
                    player.name,
                    round_data.round_number,
                )
                return False

        snapshots: Dict[str, Dict[str, Any]] = {
            player.id: deepcopy(dict(player.__dict__))
            for player, _opponent_id, _score, _color, _outcome in operations
        }
        original_results = deepcopy(round_data.results)
        original_pending_results = deepcopy(round_data.pending_results)
        original_completed = round_data.is_completed
        try:
            for player, _opponent_id, _score, _color, _outcome in operations:
                if not self._pop_player_result(player):
                    raise ValueError(f"Unable to undo result for {player.name}")
            round_data.results.clear()
            round_data.pending_results.clear()
            round_data.is_completed = False
        except Exception:
            self._restore_player_snapshots(players, snapshots)
            round_data.results[:] = original_results
            round_data.pending_results[:] = original_pending_results
            round_data.is_completed = original_completed
            logger.exception(
                "Failed to undo results for round %s; state was restored",
                round_data.round_number,
            )
            return False

        logger.info("Undid results for round %s", round_data.round_number)
        for player_id, player in players.items():
            if (
                player_id not in affected_ids
                and len(player.results) == round_data.round_number
                and player.results[-1] is None
            ):
                self._pop_player_result(player)
        return True

    @staticmethod
    def _history_matches(
        player: Player,
        opponent_id: Optional[str],
        score: float,
        color: Optional[Colour],
        outcome_type: str,
    ) -> bool:
        if not player.results or not player.opponent_ids or not player.color_history:
            return False
        if len(player.opponent_ids) != len(player.results):
            return False
        if len(player.color_history) != len(player.results):
            return False
        if player.outcome_types and len(player.outcome_types) != len(player.results):
            return False
        if player.opponent_ids[-1] != opponent_id:
            return False
        latest_result = player.results[-1]
        if latest_result is None:
            return False
        try:
            latest_score = float(latest_result)
        except (TypeError, ValueError):
            return False
        if not math.isclose(latest_score, score, abs_tol=SCORE_TOLERANCE):
            return False
        if player.color_history[-1] != color:
            return False
        if player.outcome_types and player.outcome_types[-1] != outcome_type:
            return False
        return True

    @staticmethod
    def _pop_player_result(player: Player) -> bool:
        if not player.results or not player.opponent_ids or not player.color_history:
            return False

        removed_result = player.results.pop()
        player.score -= removed_result or 0.0
        player.opponent_ids.pop()
        removed_color = player.color_history.pop()
        if player.outcome_types:
            player.outcome_types.pop()
        if player.match_history:
            player.match_history.pop()
        if player.running_scores:
            player.running_scores.pop()

        if removed_color == Colour.BLACK:
            player.num_black_games = max(0, player.num_black_games - 1)
        player.has_received_bye = any(
            opponent is None and score == WIN_SCORE
            for opponent, score in zip(player.opponent_ids, player.results)
        )
        player._opponents_played_cache = []
        return True

    def _undo_player_result(self, player: Player, round_number: int) -> bool:
        """Undo a single player's result for a round.

        Returns:
            True if successful, False otherwise
        """
        if len(player.results) < round_number:
            logger.warning(
                f"Cannot undo: {player.name} has no result for round {round_number}"
            )
            return False
        if self._pop_player_result(player):
            logger.debug(f"Undid result for {player.name} in round {round_number}")
            return True
        return False
