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

from typing import Dict, List, Optional

from gambitpairing.constants import (
    DRAW_SCORE,
    TB_ARO,
    TB_BLACK_GAMES,
    TB_BLACK_WINS,
    TB_BUCHHOLZ,
    TB_BUCHHOLZ_CUT_1,
    TB_BUCHHOLZ_MEDIAN_1,
    TB_CUMULATIVE,
    TB_CUMULATIVE_OPP,
    TB_DIRECT_ENCOUNTER,
    TB_GAMES_WON,
    TB_HEAD_TO_HEAD,
    TB_MEDIAN,
    TB_MOST_BLACKS,
    TB_PROGRESSIVE,
    TB_SOLKOFF,
    TB_SONNENBORN_BERGER,
    TB_WINS,
    WIN_SCORE,
)
from gambitpairing.player import Player
from gambitpairing.type_hints import BLACK
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


class TiebreakCalculator:
    """Calculates tiebreak scores for tournament standings.

    This class implements various tiebreak systems including:

    USCF:
    - Median Buchholz (Modified Median)
    - Solkoff (Buchholz)
    - Cumulative (Progressive)
    - Sonnenborn-Berger
    - Most Blacks
    - Head-to-Head

    FIDE (per FIDE Handbook regulations effective 1 August 2024):
    - Buchholz (8.1): Sum of opponents' scores
    - Buchholz Cut-1 (14.1): Buchholz dropping lowest opponent score
    - Buchholz Median-1 (14.3): Buchholz dropping highest and lowest
    - Progressive/Cumulative (7.5): Sum of scores after each round
    - Direct Encounter (6): Results between tied participants
    - Number of Wins (7.1): Rounds with win points (includes byes/forfeits)
    - Games Won (7.2): Games won over the board (excludes byes/forfeits)
    - Games with Black (7.3): Games played OTB with black pieces
    - Wins with Black (7.4): Games won OTB with black pieces
    - Average Rating of Opponents (10.1): Average rating, 0.5 rounds up
    - Sonnenborn-Berger (9.1): Sum of (opponent score × result against them)
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
        # USCF Tiebreakers
        player.tiebreakers[TB_MEDIAN] = self._calculate_median(player, opponent_scores)
        player.tiebreakers[TB_SOLKOFF] = sum(opponent_scores)
        player.tiebreakers[TB_CUMULATIVE] = (
            sum(player.running_scores) if player.running_scores else 0.0
        )
        player.tiebreakers[TB_CUMULATIVE_OPP] = cumulative_opp_score
        player.tiebreakers[TB_SONNENBORN_BERGER] = sb_score
        player.tiebreakers[TB_MOST_BLACKS] = self._calculate_black_games(player)
        player.tiebreakers[TB_HEAD_TO_HEAD] = 0.0  # Calculated when comparing players

        # FIDE Tiebreakers
        player.tiebreakers[TB_BUCHHOLZ] = sum(opponent_scores)  # Same as Solkoff
        player.tiebreakers[TB_BUCHHOLZ_CUT_1] = self._calculate_buchholz_cut_1(
            opponent_scores
        )
        player.tiebreakers[TB_BUCHHOLZ_MEDIAN_1] = self._calculate_buchholz_median_1(
            opponent_scores
        )
        player.tiebreakers[TB_PROGRESSIVE] = (
            sum(player.running_scores) if player.running_scores else 0.0
        )  # Same as Cumulative
        player.tiebreakers[TB_DIRECT_ENCOUNTER] = 0.0  # Calculated when comparing
        player.tiebreakers[TB_WINS] = self._calculate_wins(player)
        player.tiebreakers[TB_GAMES_WON] = self._calculate_games_won(player)
        player.tiebreakers[TB_BLACK_GAMES] = self._calculate_black_games(player)
        player.tiebreakers[TB_BLACK_WINS] = self._calculate_black_wins(player)
        player.tiebreakers[TB_ARO] = self._calculate_aro(opponents)

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
        valid_results: List[float] = []
        for i, opp_id in enumerate(player.opponent_ids):
            if opp_id is not None and i < len(player.results):
                result = player.results[i]
                if result is not None:
                    valid_results.append(result)

        score_from_games = sum(valid_results) if valid_results else 0.0
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

    def _calculate_buchholz_cut_1(self, opponent_scores: List[float]) -> float:
        """Calculate Buchholz Cut-1 (FIDE).

        Drop the lowest opponent score.

        Args:
            opponent_scores: List of opponent scores

        Returns:
            The Buchholz Cut-1 score
        """
        if not opponent_scores:
            return 0.0

        if len(opponent_scores) == 1:
            return opponent_scores[0]

        sorted_scores = sorted(opponent_scores)
        # Drop the lowest score
        return sum(sorted_scores[1:])

    def _calculate_buchholz_median_1(self, opponent_scores: List[float]) -> float:
        """Calculate Buchholz Median-1 (FIDE).

        Drop both the highest and lowest opponent scores.

        Args:
            opponent_scores: List of opponent scores

        Returns:
            The Buchholz Median-1 score
        """
        if not opponent_scores:
            return 0.0

        if len(opponent_scores) <= 2:
            # If 1 or 2 opponents, can't drop both ends
            return sum(opponent_scores)

        sorted_scores = sorted(opponent_scores)
        # Drop both highest and lowest
        return sum(sorted_scores[1:-1])

    def _calculate_wins(self, player: Player) -> float:
        """Calculate number of wins (FIDE 7.1).

        FIDE definition: The number of rounds where a participant obtains,
        with or without playing, as many points as awarded for a win.
        This includes byes and forfeits that award a full point.

        Args:
            player: The player to calculate for

        Returns:
            The number of rounds with win points
        """
        wins = 0.0
        for result in player.results:
            if result == WIN_SCORE:
                wins += 1.0
        return wins

    def _calculate_games_won(self, player: Player) -> float:
        """Calculate number of games won over the board (FIDE 7.2).

        FIDE definition: The number of games won over the board.
        This excludes byes and forfeits.

        Args:
            player: The player to calculate for

        Returns:
            The number of games won OTB
        """
        games_won = 0.0
        for i, result in enumerate(player.results):
            # Only count games played over the board (with an opponent)
            if i < len(player.opponent_ids) and player.opponent_ids[i] is not None:
                if result == WIN_SCORE:
                    games_won += 1.0
        return games_won

    def _calculate_black_games(self, player: Player) -> float:
        """Calculate number of games played with black pieces (FIDE 7.3).

        FIDE definition: The number of games played over the board with the black pieces.

        Args:
            player: The player to calculate for

        Returns:
            The number of games played with black
        """
        black_games = 0.0
        for i, color in enumerate(player.color_history):
            # Only count games played over the board (with an opponent)
            if i < len(player.opponent_ids) and player.opponent_ids[i] is not None:
                if color == BLACK:
                    black_games += 1.0
        return black_games

    def _calculate_black_wins(self, player: Player) -> float:
        """Calculate number of wins with black pieces (FIDE 7.4).

        FIDE definition: The number of games won over the board with the black pieces.

        Args:
            player: The player to calculate for

        Returns:
            The number of wins with black
        """
        black_wins = 0.0
        for i, result in enumerate(player.results):
            # Only count games played over the board (with an opponent)
            if i < len(player.opponent_ids) and player.opponent_ids[i] is not None:
                if i < len(player.color_history) and player.color_history[i] == BLACK:
                    if result == WIN_SCORE:
                        black_wins += 1.0
        return black_wins

    def _calculate_aro(self, opponents: List[Optional[Player]]) -> float:
        """Calculate Average Rating of Opponents (FIDE).

        Average of the ratings of opponents played over the board,
        rounded to the nearest whole number (0.5 rounded up).

        Args:
            opponents: List of opponent Player objects (may contain None for byes)

        Returns:
            The average rating of opponents
        """
        actual_opponents = [opp for opp in opponents if opp is not None]
        if not actual_opponents:
            return 0.0

        ratings = [opp.rating for opp in actual_opponents if opp.rating > 0]
        if not ratings:
            return 0.0

        avg = sum(ratings) / len(ratings)
        # Round to nearest whole number, 0.5 rounds up
        return float(int(avg + 0.5))

    def _set_zero_tiebreaks(self, player: Player) -> None:
        """Set all tiebreaks to zero for a player with no games."""
        player.tiebreakers = {
            # USCF
            TB_MEDIAN: 0.0,
            TB_SOLKOFF: 0.0,
            TB_CUMULATIVE: 0.0,
            TB_CUMULATIVE_OPP: 0.0,
            TB_SONNENBORN_BERGER: 0.0,
            TB_MOST_BLACKS: 0.0,
            TB_HEAD_TO_HEAD: 0.0,
            # FIDE
            TB_BUCHHOLZ: 0.0,
            TB_BUCHHOLZ_CUT_1: 0.0,
            TB_BUCHHOLZ_MEDIAN_1: 0.0,
            TB_PROGRESSIVE: 0.0,
            TB_DIRECT_ENCOUNTER: 0.0,
            TB_WINS: 0.0,
            TB_GAMES_WON: 0.0,
            TB_BLACK_GAMES: 0.0,
            TB_BLACK_WINS: 0.0,
            TB_ARO: 0.0,
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
