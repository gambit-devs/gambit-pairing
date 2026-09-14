"""Deterministic ranking by the tournament's ordered tiebreak criteria."""

from itertools import groupby

from gambitpairing.constants import TB_DIRECT_ENCOUNTER, TB_HEAD_TO_HEAD

from .tiebreak_calculator import TiebreakCalculator


def rank_players(players, tiebreak_order):
    TiebreakCalculator().calculate_all_tiebreaks(players)
    eligible = [player for player in players.values() if player.is_active]

    def rank_group(group, criteria):
        if len(group) < 2:
            return group
        if not criteria:
            return sorted(
                group, key=lambda player: (-player.rating, player.name, player.id)
            )
        criterion, *remaining = criteria
        if criterion in {TB_DIRECT_ENCOUNTER, TB_HEAD_TO_HEAD}:
            ids = {player.id for player in group}
            if not all(
                ids - {player.id} <= set(player.opponent_ids) for player in group
            ):
                return rank_group(group, remaining)
            values = {
                player.id: sum(
                    score or 0.0
                    for opponent, score in zip(player.opponent_ids, player.results)
                    if opponent in ids
                )
                for player in group
            }
        else:
            values = {
                player.id: player.tiebreakers.get(criterion, 0.0) for player in group
            }
        result = []
        for _, subgroup in groupby(
            sorted(group, key=lambda player: values[player.id], reverse=True),
            key=lambda player: values[player.id],
        ):
            result.extend(rank_group(list(subgroup), remaining))
        return result

    result = []
    for _, group in groupby(
        sorted(eligible, key=lambda player: player.score, reverse=True),
        key=lambda player: player.score,
    ):
        result.extend(rank_group(list(group), list(tiebreak_order)))
    return result
