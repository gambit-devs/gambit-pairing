"""Isolated, cancellable pairing work. This module never imports Qt."""

from collections.abc import Mapping
import os
from typing import Any

from gambitpairing.representation.tournament import tournament_from_dict
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)

_MISSING = object()
_IGNORED_PLAYER_FIELDS = frozenset({"pairing_number"})
# These fields can contain personal information. The field name is retained so
# the log says what changed, but the values never leave the process.
_SENSITIVE_PLAYER_FIELDS = frozenset(
    {
        "name",
        "phone",
        "email",
        "club",
        "dob",
        "date_of_birth",
        "cfc_id",
        "fide_id",
    }
)


def _field_diff(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    sensitive_fields: frozenset[str] = frozenset(),
    ignored_fields: frozenset[str] = frozenset(),
) -> dict[str, dict[str, Any]]:
    """Return a safe, field-level diff between two serialized objects."""
    changes: dict[str, dict[str, Any]] = {}
    for field_name in sorted(set(before) | set(after)):
        if field_name in ignored_fields:
            continue
        old_value = before.get(field_name, _MISSING)
        new_value = after.get(field_name, _MISSING)
        if old_value == new_value:
            continue
        if field_name in sensitive_fields:
            old_value = new_value = "<redacted>"
        else:
            if old_value is _MISSING:
                old_value = "<missing>"
            if new_value is _MISSING:
                new_value = "<missing>"
        changes[field_name] = {"before": old_value, "after": new_value}
    return changes


def _player_field_diff(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    """Return changed player fields without exposing contact or identity data."""
    return _field_diff(
        before,
        after,
        sensitive_fields=_SENSITIVE_PLAYER_FIELDS,
        ignored_fields=_IGNORED_PLAYER_FIELDS,
    )


def _players_by_id(document: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    """Index serialized players for safe concurrency diagnostics."""
    players = document.get("players", [])
    if not isinstance(players, list):
        return {}
    return {
        str(player.get("id")): player
        for player in players
        if isinstance(player, Mapping) and player.get("id") is not None
    }


def _document_change_summary(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> dict[str, Any]:
    """Summarize a changed tournament document without dumping its contents."""
    summary: dict[str, Any] = {}
    before_config = before.get("config", {})
    after_config = after.get("config", {})
    if isinstance(before_config, Mapping) and isinstance(after_config, Mapping):
        config_diff = _field_diff(
            before_config,
            after_config,
            sensitive_fields=frozenset({"name"}),
        )
        if config_diff:
            summary["config"] = config_diff
    before_players = _players_by_id(before)
    after_players = _players_by_id(after)
    player_diff: dict[str, Any] = {}
    for player_id in sorted(set(before_players) | set(after_players)):
        changes = _player_field_diff(
            before_players.get(player_id, {}), after_players.get(player_id, {})
        )
        if changes:
            player_diff[player_id] = {
                "player_id": player_id,
                "field_diff": changes,
            }
    if player_diff:
        summary["players"] = player_diff
    before_rounds = before.get("rounds", [])
    after_rounds = after.get("rounds", [])
    if before_rounds != after_rounds:
        summary["rounds"] = {
            "before_count": (
                len(before_rounds) if isinstance(before_rounds, list) else None
            ),
            "after_count": (
                len(after_rounds) if isinstance(after_rounds, list) else None
            ),
        }
    if not summary:
        summary["changed_sections"] = sorted(
            key for key in set(before) | set(after) if before.get(key) != after.get(key)
        )
    return summary


def _raise_pairing_validation_error(
    round_number: int,
    message: str,
    *,
    details: Any = None,
    player_id: str | None = None,
) -> None:
    """Log a safe rejection diagnostic and raise the public validation error."""
    if player_id is not None:
        log_message = (
            "Pairing generation validation failed: round=%s player_id=%s "
            "reason=%s"
        )
        log_args: tuple[Any, ...] = (round_number, player_id, message)
        if details is not None:
            log_message += " details=%s"
            log_args += (details,)
        logger.error(log_message, *log_args)
    elif details is None:
        logger.error(
            "Pairing generation validation failed: round=%s reason=%s",
            round_number,
            message,
        )
    else:
        logger.error(
            "Pairing generation validation failed: round=%s reason=%s details=%s",
            round_number,
            message,
            details,
        )
    raise ValueError(f"{message} for round {round_number}")


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
    round_number = round_index + 1
    try:
        # A separate process group lets cancellation stop BBP children as well.
        if os.name == "posix":
            os.setsid()
        connection.send(generate_pairing_document(document, round_index))
    except Exception as error:
        # Keep the traceback here: the GUI only receives a small IPC-safe error
        # payload, while this record is what makes worker failures diagnosable.
        logger.exception(
            "Pairing generation worker failed: round=%s error_type=%s",
            round_number,
            type(error).__name__,
        )
        connection.send({"error": str(error)})
    finally:
        connection.close()


def commit_pairing_document(tournament, expected, result):
    round_number = tournament.get_completed_rounds() + 1
    current = tournament.to_dict()
    if current != expected:
        _raise_pairing_validation_error(
            round_number,
            "Tournament changed while pairings were generated",
            details=_document_change_summary(expected, current),
        )
    prepared = tournament_from_dict(result["document"])
    if set(prepared.players) != set(tournament.players):
        _raise_pairing_validation_error(
            round_number,
            "Pairing job changed the roster",
            details={
                "removed_player_ids": sorted(
                    set(tournament.players) - set(prepared.players)
                ),
                "added_player_ids": sorted(
                    set(prepared.players) - set(tournament.players)
                ),
            },
        )
    original_rounds = expected.get("rounds", [])[: tournament.get_completed_rounds()]
    if result["document"].get("rounds", [])[:-1] != original_rounds:
        _raise_pairing_validation_error(
            round_number,
            "Pairing job changed completed rounds",
            details={
                "completed_round_count": tournament.get_completed_rounds(),
            },
        )
    if prepared.config.to_dict() != tournament.config.to_dict():
        _raise_pairing_validation_error(
            round_number,
            "Pairing job changed tournament configuration",
            details=_field_diff(
                tournament.config.to_dict(),
                prepared.config.to_dict(),
                sensitive_fields=frozenset({"name"}),
            ),
        )
    for key, player in prepared.players.items():
        before = tournament.players[key].to_dict()
        after = player.to_dict()
        changes = _player_field_diff(before, after)
        if changes:
            _raise_pairing_validation_error(
                round_number,
                f"Pairing job changed player data for player {key}",
                details={"player_id": key, "field_diff": changes},
                player_id=key,
            )
    if len(prepared.rounds) != tournament.get_completed_rounds() + 1:
        _raise_pairing_validation_error(
            round_number,
            "Pairing job returned an unexpected round count",
            details={
                "expected_count": tournament.get_completed_rounds() + 1,
                "actual_count": len(prepared.rounds),
            },
        )
    latest = prepared.rounds[-1]
    next_index = tournament.get_completed_rounds()
    scheduled = (
        tournament.rounds[next_index].scheduled_byes
        if next_index < len(tournament.rounds)
        else {}
    )
    if latest.scheduled_byes != scheduled:
        _raise_pairing_validation_error(
            round_number,
            "Pairing job changed scheduled byes",
            details={"before": scheduled, "after": latest.scheduled_byes},
        )
    if latest.is_completed or latest.results or latest.pending_results:
        _raise_pairing_validation_error(
            round_number,
            "Pairing job returned results instead of an unplayed round",
            details={
                "is_completed": latest.is_completed,
                "result_count": len(latest.results),
                "pending_result_count": len(latest.pending_results),
            },
        )
    if latest.round_number != next_index + 1:
        _raise_pairing_validation_error(
            round_number,
            "Pairing job returned an unexpected round number",
            details={
                "expected_round": next_index + 1,
                "actual_round": latest.round_number,
            },
        )
    assigned = [key for pair in latest.pairings for key in pair]
    if latest.bye_player_id:
        assigned.append(latest.bye_player_id)
    eligible = {player.id for player in prepared.get_player_list(active_only=True)}
    eligible.difference_update(
        key for ids in latest.scheduled_byes.values() for key in ids
    )
    if len(assigned) != len(set(assigned)) or set(assigned) != eligible:
        _raise_pairing_validation_error(
            round_number,
            "Pairing job did not assign every active player exactly once",
            details={
                "assigned_player_ids": assigned,
                "eligible_player_ids": sorted(eligible),
            },
        )
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
            _raise_pairing_validation_error(
                round_number,
                "Pairing job violates absolute pairing criteria",
                details={
                    "violation_count": len(report.violations),
                    "criteria": [
                        violation.criterion_id for violation in report.violations
                    ],
                },
            )
    tournament.rounds = prepared.rounds
    tournament._rebuild_pairing_history()
    tournament.num_rounds = prepared.num_rounds
    for key, player in prepared.players.items():
        tournament.players[key].pairing_number = player.pairing_number
    return result.get("engine", tournament.pairing_system)
