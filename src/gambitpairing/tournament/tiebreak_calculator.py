"""Tiebreak calculation for tournaments.

This module handles calculation of various tiebreak systems used in chess tournaments.
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

from typing import Dict, List

from gambitpairing.constants import (
    DRAW_SCORE,
    TB_CUMULATIVE,
    TB_CUMULATIVE_OPP,
    TB_HEAD_TO_HEAD,
    TB_MEDIAN,
    TB_MOST_BLACKS,
    TB_SOLKOFF,
    TB_SONNENBORN_BERGER,
    WIN_SCORE,
)
from gambitpairing.player import Player
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


class TiebreakCalculator:
    """Calculates tiebreak scores for tournament standings.

    This class implements various tiebreak systems including:
    - Median Buchholz (Modified Median)
    - Solkoff (Buchholz)
    - Cumulative (Progressive)
    - Sonnenborn-Berger
    - Most Blacks
    - Head-to-Head
    """

    def calculate_all_tiebreaks(self, players: Dict[str, Player]) -> None:
        """Calculate all tiebreaks for all players.

        Args:
            players: Dictionary of all players (id -> Player)
        """
        for player in players.values():
            if not player.is_active and not player.results:
                # Skip players with no history
                player.tiebreakers = {}
                continue

            self.calculate_player_tiebreaks(player, players)

    def calculate_player_tiebreaks(
        self, player: Player, all_players: Dict[str, Player]
    ) -> None:
        """Calculate all tiebreak scores for a single player.

        Args:
            player: The player to calculate tiebreaks for
            all_players: Dictionary of all players for opponent lookups
        """
        player.tiebreakers = {}

        # Get opponent information
        opponents = player.get_opponent_objects(all_players)
        actual_opponents = [opp for opp in opponents if opp is not None]

        if not actual_opponents:
            # No games played, all tiebreaks are 0
            self._set_zero_tiebreaks(player)
            return

        # Calculate opponent scores and game-specific data
        opponent_scores = []
        sb_score = 0.0
        cumulative_opp_score = 0.0

        for i, opponent in enumerate(opponents):
            if opponent is None:
                continue  # Skip bye

            opp_score = all_players[opponent.id].score
            opponent_scores.append(opp_score)
            cumulative_opp_score += opp_score

            # Sonnenborn-Berger: multiply opponent score by player's result
            if i < len(player.results):
                result = player.results[i]
                if result == WIN_SCORE:
                    sb_score += opp_score
                elif result == DRAW_SCORE:
                    sb_score += 0.5 * opp_score

        # Calculate individual tiebreaks
        player.tiebreakers[TB_MEDIAN] = self._calculate_median(player, opponent_scores)
        player.tiebreakers[TB_SOLKOFF] = sum(opponent_scores)
        player.tiebreakers[TB_CUMULATIVE] = (
            sum(player.running_scores) if player.running_scores else 0.0
        )
        player.tiebreakers[TB_CUMULATIVE_OPP] = cumulative_opp_score
        player.tiebreakers[TB_SONNENBORN_BERGER] = sb_score
        player.tiebreakers[TB_MOST_BLACKS] = float(player.num_black_games)
        player.tiebreakers[TB_HEAD_TO_HEAD] = 0.0  # Calculated when comparing players

    def _calculate_median(self, player: Player, opponent_scores: List[float]) -> float:
        """Calculate Modified Median (USCF Median Buchholz).

        USCF Rule 34E3:
        - If player scored >50%, drop lowest opponent score
        - If player scored <50%, drop highest opponent score
        - If player scored exactly 50%, drop both highest and lowest

        Args:
            player: The player to calculate for
            opponent_scores: List of opponent scores

        Returns:
            The median buchholz score
        """
        if not opponent_scores:
            return 0.0

        if len(opponent_scores) == 1:
            return opponent_scores[0]

        # Calculate player's percentage from played games (excluding byes)
        score_from_games = sum(
            player.results[i]
            for i, opp_id in enumerate(player.opponent_ids)
            if opp_id is not None and i < len(player.results)
        )
        games_played = len([opp for opp in player.opponent_ids if opp is not None])
        max_possible = float(games_played)

        if max_possible == 0:
            return sum(opponent_scores)

        sorted_scores = sorted(opponent_scores)
        percentage = score_from_games / max_possible

        if percentage > 0.5:
            # Drop lowest
            return sum(sorted_scores[1:])
        elif percentage < 0.5:
            # Drop highest
            return sum(sorted_scores[:-1])
        else:
            # Drop both highest and lowest (exactly 50%)
            if len(sorted_scores) >= 3:
                return sum(sorted_scores[1:-1])
            else:
                # If only 2 opponents, sum is 0 after dropping both
                return 0.0

    def _set_zero_tiebreaks(self, player: Player) -> None:
        """Set all tiebreaks to zero for a player with no games."""
        player.tiebreakers = {
            TB_MEDIAN: 0.0,
            TB_SOLKOFF: 0.0,
            TB_CUMULATIVE: 0.0,
            TB_CUMULATIVE_OPP: 0.0,
            TB_SONNENBORN_BERGER: 0.0,
            TB_MOST_BLACKS: 0.0,
            TB_HEAD_TO_HEAD: 0.0,
        }

    def calculate_head_to_head(
        self, player1: Player, player2: Player
    ) -> tuple[bool, bool]:
        """Calculate head-to-head results between two players.

        Args:
            player1: First player
            player2: Second player

        Returns:
            Tuple of (player1_won, player2_won) booleans
        """
        p1_won = False
        p2_won = False

        for i, opp_id in enumerate(player1.opponent_ids):
            if opp_id == player2.id and i < len(player1.results):
                result = player1.results[i]
                if result == WIN_SCORE:
                    p1_won = True
                elif result == 0.0:  # Loss
                    p2_won = True

        return p1_won, p2_won
