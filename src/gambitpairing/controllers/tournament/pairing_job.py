"""Isolated, cancellable pairing work. This module never imports Qt."""

import os

from gambitpairing.representation.tournament import tournament_from_dict


def generate_pairing_document(document, round_index):
    tournament = tournament_from_dict(document)
    if round_index != tournament.get_completed_rounds():
        raise ValueError("Only the next uncompleted round can be paired")
    tournament.clear_rounds_from(round_index)
    tournament.create_pairings(round_index + 1, lambda *_: False)
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
    if len(prepared.rounds) != tournament.get_completed_rounds() + 1:
        raise ValueError("Pairing job returned an unexpected round count")
    latest = prepared.rounds[-1]
    assigned = [key for pair in latest.pairings for key in pair]
    if latest.bye_player_id:
        assigned.append(latest.bye_player_id)
    eligible = {player.id for player in prepared.get_player_list(active_only=True)}
    if len(assigned) != len(set(assigned)) or set(assigned) != eligible:
        raise ValueError("Pairing job did not assign every active player exactly once")
    tournament.rounds = prepared.rounds
    tournament.num_rounds = prepared.num_rounds
    for key, player in prepared.players.items():
        tournament.players[key].pairing_number = player.pairing_number
    return result.get("engine", tournament.pairing_system)
