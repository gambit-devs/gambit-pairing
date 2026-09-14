"""Deterministic ranking by the tournament's ordered tiebreak criteria."""

from itertools import groupby

from gambitpairing.constants import (
    MODE_FIDE,
    TB_ARO,
    TB_DIRECT_ENCOUNTER,
    TB_HEAD_TO_HEAD,
)

from .tiebreak_calculator import TiebreakCalculator


def rank_players(
    players, tiebreak_order, mode=MODE_FIDE, rounds=None, pairing_system="dutch_swiss"
):
    calculator = TiebreakCalculator(mode, rounds, pairing_system)
    calculator.calculate_all_tiebreaks(players)
    eligible = [player for player in players.values() if player.is_active]
    criteria_order = list(tiebreak_order)
    if mode == MODE_FIDE and any(player.rating <= 0 for player in players.values()):
        criteria_order = [key for key in criteria_order if key != TB_ARO]

    def rank_group(group, criteria):
        if len(group) < 2:
            return [group]
        if not criteria:
            return [
                sorted(
                    group, key=lambda player: (-player.rating, player.name, player.id)
                )
            ]
        criterion, *remaining = criteria
        if criterion in {TB_DIRECT_ENCOUNTER, TB_HEAD_TO_HEAD}:
            ids = {player.id for player in group}
            values, met = {}, {}
            for player in group:
                encounters = {}
                for index, (opponent, score) in enumerate(
                    zip(player.opponent_ids, player.results)
                ):
                    if rounds is not None and index >= rounds:
                        break
                    if (
                        opponent in ids
                        and score is not None
                        and (
                            criterion == TB_HEAD_TO_HEAD
                            or pairing_system == "round_robin"
                            or calculator._played(player, index)
                        )
                    ):
                        encounters.setdefault(opponent, []).append(score)
                met[player.id] = set(encounters)
                values[player.id] = sum(
                    (
                        sum(scores) / len(scores)
                        if criterion == TB_DIRECT_ENCOUNTER
                        else sum(2 * score - 1 for score in scores)
                    )
                    for scores in encounters.values()
                )
            if criterion == TB_DIRECT_ENCOUNTER and not all(
                ids - {player.id} <= met[player.id] for player in group
            ):
                winners = [
                    player
                    for player in group
                    if all(
                        values[player.id]
                        > values[other.id] + len(ids - {other.id} - met[other.id])
                        for other in group
                        if other is not player
                    )
                ]
                if not winners:
                    return rank_group(group, remaining)
                winner = winners[0]
                return [[winner]] + rank_group(
                    [p for p in group if p is not winner], criteria
                )
        else:
            values = {
                player.id: player.tiebreakers.get(criterion, 0.0) for player in group
            }
        result = []
        subgroups = [
            list(subgroup)
            for _, subgroup in groupby(
                sorted(group, key=lambda player: values[player.id], reverse=True),
                key=lambda player: values[player.id],
            )
        ]
        for subgroup in subgroups:
            next_criteria = (
                criteria
                if criterion == TB_DIRECT_ENCOUNTER and len(subgroups) > 1
                else remaining
            )
            result.extend(rank_group(subgroup, next_criteria))
        return result

    result = []
    for _, group in groupby(
        sorted(eligible, key=lambda player: player.score, reverse=True),
        key=lambda player: player.score,
    ):
        result.extend(rank_group(list(group), criteria_order))
    ordered = []
    for tied in result:
        rank = len(ordered) + 1
        for player in tied:
            player.standing_rank = rank
            player.standing_tie_size = len(tied)
        ordered.extend(tied)
    return ordered
