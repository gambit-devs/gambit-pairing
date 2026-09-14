"""Isolated, cancellable pairing work. This module never imports Qt."""

import os

from gambitpairing.representation.tournament import tournament_from_dict


def generate_pairing_document(document, round_index):
    tournament = tournament_from_dict(document)
    if round_index != tournament.get_completed_rounds():
        raise ValueError("Only the next uncompleted round can be paired")
    scheduled = (
        tournament.rounds[round_index].scheduled_byes
        if round_index < len(tournament.rounds)
        else {}
    )
    tournament.clear_rounds_from(round_index)
    statuses = {key: player.is_active for key, player in tournament.players.items()}
    try:
        for ids in scheduled.values():
            for key in ids:
                tournament.players[key].is_active = False
        tournament.create_pairings(round_index + 1, lambda *_: False)
        tournament.rounds[-1].scheduled_byes = scheduled
    finally:
        for key, status in statuses.items():
            tournament.players[key].is_active = status
    return {
        "document": tournament.to_dict(),
        "engine": tournament.round_controller.last_engine,
        "fallback_reason": tournament.round_controller.fallback_reason,
    }


def run_pairing_process(connection, document, round_index):
    # A separate process group lets cancellation stop BBP children as well.
    if os.name == "posix":
        os.setsid()
    try:
        connection.send(generate_pairing_document(document, round_index))
    except Exception as error:
        connection.send({"error": str(error)})
    finally:
        connection.close()


def commit_pairing_document(tournament, expected, result):
    if tournament.to_dict() != expected:
        raise ValueError("Tournament changed while pairings were generated")
    prepared = tournament_from_dict(result["document"])
    if set(prepared.players) != set(tournament.players):
        raise ValueError("Pairing job changed the roster")
    original_rounds = expected.get("rounds", [])[: tournament.get_completed_rounds()]
    if result["document"].get("rounds", [])[:-1] != original_rounds:
        raise ValueError("Pairing job changed completed rounds")
    if prepared.config.to_dict() != tournament.config.to_dict():
        raise ValueError("Pairing job changed tournament configuration")
    for key, player in prepared.players.items():
        before = tournament.players[key].to_dict()
        after = player.to_dict()
        before.pop("pairing_number", None)
        after.pop("pairing_number", None)
        if before != after:
            raise ValueError("Pairing job changed player data")
    if len(prepared.rounds) != tournament.get_completed_rounds() + 1:
        raise ValueError("Pairing job returned an unexpected round count")
    latest = prepared.rounds[-1]
    next_index = tournament.get_completed_rounds()
    scheduled = (
        tournament.rounds[next_index].scheduled_byes
        if next_index < len(tournament.rounds)
        else {}
    )
    if latest.scheduled_byes != scheduled:
        raise ValueError("Pairing job changed scheduled byes")
    if latest.is_completed or latest.results or latest.pending_results:
        raise ValueError("Pairing job returned results instead of an unplayed round")
    if latest.round_number != next_index + 1:
        raise ValueError("Pairing job returned an unexpected round number")
    assigned = [key for pair in latest.pairings for key in pair]
    if latest.bye_player_id:
        assigned.append(latest.bye_player_id)
    eligible = {player.id for player in prepared.get_player_list(active_only=True)}
    eligible.difference_update(
        key for ids in latest.scheduled_byes.values() for key in ids
    )
    if len(assigned) != len(set(assigned)) or set(assigned) != eligible:
        raise ValueError("Pairing job did not assign every active player exactly once")
    if tournament.pairing_system == "dutch_swiss":
        from .replay import round_snapshot
        from gambitpairing.validation.fpc import create_fpc_validator

        roster, active, previous, byes = round_snapshot(
            expected["players"], expected["rounds"], latest.round_number
        )
        by_id = {player.id: player for player in roster}
        excluded = {key for ids in latest.scheduled_byes.values() for key in ids}
        active = [p for p in active if p.id not in excluded]
        report = create_fpc_validator().validate_round_pairings(
            [(by_id[w], by_id[b]) for w, b in latest.pairings],
            by_id.get(latest.bye_player_id),
            latest.round_number,
            tournament.num_rounds,
            previous,
            byes,
            players=active,
        )
        if report.violations:
            raise ValueError("Pairing job violates absolute pairing criteria")
    tournament.rounds = prepared.rounds
    tournament._rebuild_pairing_history()
    tournament.num_rounds = prepared.num_rounds
    for key, player in prepared.players.items():
        tournament.players[key].pairing_number = player.pairing_number
    return result.get("engine", tournament.pairing_system)
