"""Federation-specific tiebreaks over round-indexed result histories.

FIDE C.07 (2026-03-01); US Chess Rule 34 (2026 online edition).
Opponent adjustments never change tournament scores.
"""

from gambitpairing import constants as c
from gambitpairing.models.enums import Colour


class TiebreakCalculator:
    def __init__(self, mode=c.MODE_FIDE, rounds=None, pairing_system="dutch_swiss"):
        self.mode = mode
        self.rounds = rounds
        self.pairing_system = pairing_system

    def _type_b_played(self, player, index):
        return self._played(player, index) or (
            self.mode == c.MODE_FIDE
            and self.pairing_system == "round_robin"
            and self._opponent(player, index) is not None
            and self._result(player, index) == 1
        )

    @staticmethod
    def _result(player, index):
        return player.results[index] if index < len(player.results) else None

    @staticmethod
    def _opponent(player, index):
        return player.opponent_ids[index] if index < len(player.opponent_ids) else None

    @classmethod
    def _played(cls, player, index):
        outcomes = getattr(player, "outcome_types", [])
        return (
            cls._result(player, index) is not None
            and cls._opponent(player, index) is not None
            and (index >= len(outcomes) or outcomes[index] == c.OUTCOME_NORMAL_GAME)
        )

    @classmethod
    def _voluntary(cls, player, index):
        return not cls._played(player, index) and (cls._result(player, index) or 0) < 1

    def _adjusted(self, player, rounds, fide):
        total = 0.0
        for index in range(rounds):
            score = self._result(player, index) or 0.0
            if not self._played(player, index):
                if not fide:
                    score = 0.5
                elif (
                    self._opponent(player, index) is None
                    and score < 1
                    and all(
                        self._voluntary(player, later)
                        for later in range(index + 1, rounds)
                    )
                ):
                    score = 0.5
            total += score
        return total

    def _progressive(self, player, rounds, uscf=False):
        running = total = 0.0
        for index in range(rounds):
            score = self._result(player, index) or 0.0
            running += score
            total += running
            if uscf and not self._played(player, index):
                total -= score
        return total

    def calculate_all_tiebreaks(self, players):
        """Return tiebreak values keyed by player ID without mutating players."""
        rounds = self.rounds
        if rounds is None:
            rounds = max((len(p.results) for p in players.values()), default=0)
        tiebreakers = {}
        for player in players.values():
            tiebreakers[player.id] = self.calculate_player_tiebreaks(
                player, players, rounds
            )
        return tiebreakers

    def calculate_player_tiebreaks(self, player, all_players, rounds=None):
        """Calculate one player's values without storing them on the player."""
        if rounds is None:
            rounds = (
                self.rounds
                if self.rounds is not None
                else max((len(p.results) for p in all_players.values()), default=0)
            )
        uscf_scores, fide_scores, voluntary = [], [], []
        uscf_sb = fide_sb = opposition = 0.0
        played_opponents = []
        own_score = sum(self._result(player, i) or 0 for i in range(rounds))
        for index in range(rounds):
            opponent = all_players.get(self._opponent(player, index))
            score = self._result(player, index) or 0.0
            if self._played(player, index) and opponent is not None:
                uscf_scores.append(self._adjusted(opponent, rounds, False))
                contribution = self._adjusted(opponent, rounds, True)
                uscf_sb += (
                    sum(self._result(opponent, i) or 0 for i in range(rounds)) * score
                )
                opposition += self._progressive(opponent, rounds, uscf=True)
                played_opponents.append(opponent)
            else:
                uscf_scores.append(0.0)
                cap = (
                    self._adjusted(opponent, rounds, True) if opponent else rounds * 0.5
                )
                contribution = min(own_score, cap)
            fide_scores.append(contribution)
            voluntary.append(self._voluntary(player, index))
            if self.pairing_system == "round_robin":
                fide_sb += (
                    (sum(self._result(opponent, i) or 0 for i in range(rounds)) * score)
                    if opponent
                    else 0
                )
            else:
                fide_sb += contribution * score

        black_games = sum(
            self._type_b_played(player, i) and color == Colour.BLACK
            for i, color in enumerate(player.color_history[:rounds])
        )
        black_wins = sum(
            self._type_b_played(player, i)
            and color == Colour.BLACK
            and self._result(player, i) == 1
            for i, color in enumerate(player.color_history[:rounds])
        )
        ratings = [p.rating for p in played_opponents]
        aro = (
            float(int(sum(ratings) / len(ratings) + 0.5))
            if ratings and all(r > 0 for r in ratings)
            else 0.0
        )
        cut = list(zip(fide_scores, voluntary))
        if cut:
            candidates = [i for i, (_, vur) in enumerate(cut) if vur] or list(
                range(len(cut))
            )
            cut.pop(min(candidates, key=lambda i: cut[i][0]))
        median = list(cut)
        if median:
            median.pop(max(range(len(median)), key=lambda i: median[i][0]))
        tiebreakers = {
            c.TB_MEDIAN: self._calculate_median(player, uscf_scores),
            c.TB_SOLKOFF: sum(uscf_scores),
            c.TB_CUMULATIVE: self._progressive(player, rounds, uscf=True),
            c.TB_CUMULATIVE_OPP: opposition,
            c.TB_SONNENBORN_BERGER: fide_sb if self.mode == c.MODE_FIDE else uscf_sb,
            c.TB_MOST_BLACKS: float(black_games),
            c.TB_HEAD_TO_HEAD: 0.0,
            c.TB_BUCHHOLZ: sum(fide_scores),
            c.TB_BUCHHOLZ_CUT_1: sum(value for value, _ in cut),
            c.TB_BUCHHOLZ_MEDIAN_1: sum(value for value, _ in median),
            c.TB_PROGRESSIVE: self._progressive(player, rounds),
            c.TB_DIRECT_ENCOUNTER: 0.0,
            c.TB_WINS: float(sum(self._result(player, i) == 1 for i in range(rounds))),
            c.TB_GAMES_WON: float(
                sum(
                    self._type_b_played(player, i) and self._result(player, i) == 1
                    for i in range(rounds)
                )
            ),
            c.TB_BLACK_GAMES: float(black_games),
            c.TB_BLACK_WINS: float(black_wins),
            c.TB_ARO: aro,
        }
        return tiebreakers

    def _calculate_median(self, player, opponent_scores):
        scores = sorted(opponent_scores)
        count = 2 if len(scores) >= 9 else 1
        midpoint = len(scores) * 0.5
        if player.score >= midpoint:
            scores = scores[count:]
        if player.score <= midpoint:
            scores = scores[:-count]
        return sum(scores)

    @staticmethod
    def _calculate_buchholz_cut_1(scores):
        return sum(sorted(scores)[1:])

    @staticmethod
    def _calculate_buchholz_median_1(scores):
        return sum(sorted(scores)[1:-1])

    def calculate_head_to_head(self, player1, player2):
        scores = [
            score
            for opponent, score in zip(player1.opponent_ids, player1.results)
            if opponent == player2.id
        ]
        return 1.0 in scores, 0.0 in scores
