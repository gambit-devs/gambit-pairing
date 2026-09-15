"""Canonical pre-round replay used by validation, comparison and persistence."""

from __future__ import annotations

from typing import Any

from gambitpairing.constants import OUTCOME_BYE
from gambitpairing.models.player import Player
from gambitpairing.models.tournament import MatchResult, RoundData

from .result import ResultRecorder


def fresh_player(source_player) -> Player:
    """Create a fresh player with static attributes but empty history.

    Args:
        source_player: Source player object or dict to copy attributes from

    Returns:
        New Player instance with empty history lists
    """
    if isinstance(source_player, Player):
        data = source_player.to_dict()
    else:
        data = dict(source_player)

    fresh = Player.from_dict(data)

    # Reset tournament-derived state so each comparison starts from the same
    # static player data without carrying results from the source tournament.
    fresh.score = 0.0
    fresh.opponent_ids = []
    fresh.results = []
    fresh.color_history = []
    fresh.outcome_types = []
    fresh.running_scores = []
    fresh.float_history = []
    fresh.match_history = []
    fresh.has_received_bye = False
    fresh.num_black_games = 0
    fresh.bsn = None
    fresh.is_moved_down = False
    fresh._opponents_played_cache = []
    fresh.is_active = data.get("is_active", True)

    return fresh


def replay_round(players: dict[str, Player], data: dict[str, Any]) -> None:
    """Apply a historical round once with the live recorder's outcome semantics."""
    recorder = ResultRecorder()
    results = []
    for entry in data.get("results", []):
        if isinstance(entry, dict):
            result = MatchResult.from_dict(entry)
            results.append(
                (
                    result.white_id,
                    result.black_id,
                    result.white_score,
                    result.black_score,
                    result.outcome_type,
                )
            )
        else:
            values = list(entry)
            if len(values) == 5 and isinstance(values[4], bool):
                values[4] = (
                    ("double_forfeit" if values[2] == values[3] == 0 else "forfeit_win")
                    if values[4]
                    else "normal"
                )
            results.append(tuple(values))
    round_data = RoundData(
        round_number=data["round_number"],
        pairings=[tuple(pair) for pair in data.get("pairings", [])],
        bye_player_id=data.get("bye_player_id") or data.get("bye_player"),
        bye_type=data.get("bye_type", "full"),
        scheduled_byes=data.get("scheduled_byes", {}),
    )
    # Participation in historical rounds must not depend on today's active flag.
    statuses = {key: player.is_active for key, player in players.items()}
    try:
        for player in players.values():
            player.is_active = True
        if not recorder.record_round_results(round_data, results, players):
            raise ValueError(f"Cannot replay round {round_data.round_number}")
        scheduled = data.get("scheduled_byes", {})
        assigned = {key for pair in round_data.pairings for key in pair}
        if round_data.bye_player_id:
            assigned.add(round_data.bye_player_id)
        for kind, score in (("half_point", 0.5), ("zero_point", 0.0)):
            for key in scheduled.get(kind, []):
                if key not in players or key in assigned:
                    raise ValueError("Invalid scheduled bye")
                assigned.add(key)
        # Keep all histories indexed by actual tournament round, including
        # rounds skipped by withdrawn players.
        for key, player in players.items():
            if key not in assigned:
                recorder._pad_skipped_rounds(player, data["round_number"])
    finally:
        for key, active in statuses.items():
            players[key].is_active = active


def round_snapshot(players: list, rounds: list, round_number: int):
    roster = {player.id: player for player in map(fresh_player, players)}
    previous_matches: set = set()
    bye_history: dict[str, int] = {}
    for data in sorted(rounds, key=lambda item: item["round_number"]):
        if data["round_number"] >= round_number:
            break
        replay_round(roster, data)
        for player in roster.values():
            previous_matches.update(
                frozenset((player.id, opponent))
                for i, opponent in enumerate(player.opponent_ids)
                if opponent is not None and player.outcome_types[i] == "normal"
            )
        bye_id = data.get("bye_player_id") or data.get("bye_player")
        if bye_id:
            bye_history[bye_id] = bye_history.get(bye_id, 0) + 1
    target = next(
        (item for item in rounds if item["round_number"] == round_number), None
    )
    if target is not None:
        active_ids = {key for pair in target.get("pairings", []) for key in pair}
        bye_id = target.get("bye_player_id") or target.get("bye_player")
        if bye_id:
            active_ids.add(bye_id)
        # New documents preserve eligibility independently of actual assignments.
        # Legacy documents lack withdrawal history: retain today's active players
        # as well, so a missing assignment cannot silently disappear from C4.
        if target.get("active_player_ids") is not None:
            active_ids = set(target["active_player_ids"])
        else:
            active_ids.update(key for key, player in roster.items() if player.is_active)
        scheduled = target.get("scheduled_byes", {})
        active_ids.difference_update(
            scheduled.get("half_point", []), scheduled.get("zero_point", [])
        )
        active = [player for key, player in roster.items() if key in active_ids]
    else:
        active = [player for player in roster.values() if player.is_active]
    active_ids = {player.id for player in active}
    for player in roster.values():
        player.is_active = player.id in active_ids
    return list(roster.values()), active, previous_matches, bye_history
