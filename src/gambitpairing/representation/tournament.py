"""Tournament dictionary and JSON document representation."""

from __future__ import annotations

from collections.abc import Mapping
from importlib import import_module
import json
import math
from numbers import Real
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from gambitpairing.constants import (
    DRAW_SCORE,
    LOSS_SCORE,
    OUTCOME_DOUBLE_FORFEIT,
    OUTCOME_FORFEIT_LOSS,
    OUTCOME_FORFEIT_WIN,
    OUTCOME_NORMAL_GAME,
    WIN_SCORE,
)
from gambitpairing.models.player import create_player_from_dict
from gambitpairing.models.tournament import (
    MatchResult,
    PairingHistory,
    RoundData,
    TournamentConfig,
)

CURRENT_DOCUMENT_VERSION = 1
VALID_RESULT_OUTCOMES = {
    OUTCOME_NORMAL_GAME,
    OUTCOME_FORFEIT_WIN,
    OUTCOME_FORFEIT_LOSS,
    OUTCOME_DOUBLE_FORFEIT,
}
VALID_RESULT_SCORES = {LOSS_SCORE, DRAW_SCORE, WIN_SCORE}
SCORE_TOLERANCE = 1e-9


class TournamentDocumentError(ValueError):
    """Raised when a tournament document violates the storage contract."""


def tournament_to_dict(tournament: Any) -> Dict[str, Any]:
    """Project a tournament model into JSON-safe primitives."""
    return {
        "__version__": CURRENT_DOCUMENT_VERSION,
        "config": tournament.config.to_dict(),
        "players": [player.to_dict() for player in tournament.players.values()],
        "rounds": [round_data_to_dict(round_data) for round_data in tournament.rounds],
        "pairing_history": pairing_history_to_dict(tournament.pairing_history),
    }


def tournament_from_dict(data: Mapping[str, Any]) -> Any:
    """Reconstruct a tournament from current or legacy dictionary shapes."""
    if not isinstance(data, Mapping):
        raise TournamentDocumentError("Tournament document must be an object")
    _validate_document_version(data)

    tournament_module = import_module("gambitpairing.controllers.tournament.session")
    Tournament = tournament_module.TournamentSession

    config_data = data.get("config", data)
    if not isinstance(config_data, Mapping):
        raise TournamentDocumentError("Tournament config must be an object")
    _validate_config_data(config_data)
    config = tournament_config_from_dict(dict(config_data))

    player_data_list = list(_iter_player_dicts(data.get("players", [])))
    players = _load_players(player_data_list)
    player_ids = {player.id for player in players}

    tournament = Tournament(
        name=config.name,
        players=players,
        num_rounds=config.num_rounds,
        tiebreak_order=config.tiebreak_order,
        pairing_system=config.pairing_system,
        use_experimental_dutch=config.use_experimental_dutch,
        tournament_mode=config.tournament_mode,
        fide_strict=config.fide_strict,
    )
    tournament.config = config
    tournament.round_controller.pairing_system = config.pairing_system
    tournament.round_controller.num_rounds = config.num_rounds
    tournament.round_controller.fide_strict = config.fide_strict
    tournament.round_controller.use_experimental_dutch = config.use_experimental_dutch

    if "rounds" in data:
        raw_rounds = data["rounds"]
    else:
        raw_rounds = [
            round_data.to_dict() for round_data in _legacy_rounds_from_dict(data)
        ]
    tournament.rounds = _load_rounds(raw_rounds, player_ids)
    if len(tournament.rounds) > config.num_rounds:
        raise TournamentDocumentError("More rounds than configured")
    incomplete_seen = False
    for item in tournament.rounds:
        if incomplete_seen and item.is_completed:
            raise TournamentDocumentError(
                "Completed rounds must be a consecutive prefix"
            )
        incomplete_seen = incomplete_seen or not item.is_completed

    manual_adjustments = _load_manual_adjustments(data, len(tournament.rounds))
    tournament.pairing_history.manual_adjustments = manual_adjustments

    for player in tournament.players.values():
        player._opponents_played_cache = []

    from gambitpairing.controllers.tournament.replay import fresh_player, replay_round

    rebuilt = {
        player.id: fresh_player(player) for player in tournament.players.values()
    }
    for item in tournament.rounds:
        if item.is_completed:
            replay_round(rebuilt, item.to_dict())
    derived_fields = (
        "score",
        "results",
        "opponent_ids",
        "outcome_types",
        "color_history",
        "running_scores",
        "match_history",
        "has_received_bye",
        "num_black_games",
        "tiebreakers",
        "float_history",
        "is_moved_down",
    )
    for player_id, player in tournament.players.items():
        for field_name in derived_fields:
            setattr(player, field_name, getattr(rebuilt[player_id], field_name))

    return tournament


def save_tournament_document(
    path: str | Path,
    tournament: Any,
    gui_state: Optional[Dict[str, Any]] = None,
) -> None:
    """Save a tournament JSON document."""
    data = tournament_to_dict(tournament)
    if gui_state is not None:
        data["gui_state"] = gui_state
    serialized = json.dumps(data, indent=4, allow_nan=False)
    target = Path(path)
    target_parent = target.parent
    if not target_parent.exists() or not target_parent.is_dir():
        raise OSError(f"Directory does not exist: {target_parent}")

    temporary_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target_parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(serialized)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, target)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass


def load_tournament_document(path: str | Path) -> Tuple[Any, Dict[str, Any]]:
    """Load a tournament JSON document and return model plus GUI state."""
    try:
        data = json.loads(
            Path(path).read_text(encoding="utf-8"),
            parse_constant=_reject_json_constant,
        )
    except json.JSONDecodeError as error:
        raise TournamentDocumentError(f"Invalid tournament JSON: {error}") from error
    if not isinstance(data, Mapping):
        raise TournamentDocumentError("Tournament document must be an object")
    gui_state = data.get("gui_state", {})
    if not isinstance(gui_state, Mapping):
        raise TournamentDocumentError("GUI state must be an object")
    return tournament_from_dict(data), dict(gui_state)


def tournament_config_to_dict(config: TournamentConfig) -> Dict[str, Any]:
    return config.to_dict()


def tournament_config_from_dict(data: Dict[str, Any]) -> TournamentConfig:
    return TournamentConfig.from_dict(data)


def round_data_to_dict(round_data: RoundData) -> Dict[str, Any]:
    return round_data.to_dict()


def round_data_from_dict(data: Dict[str, Any]) -> RoundData:
    return RoundData.from_dict(data)


def match_result_to_dict(match_result: MatchResult) -> Dict[str, Any]:
    return match_result.to_dict()


def match_result_from_dict(data: Dict[str, Any]) -> MatchResult:
    return MatchResult.from_dict(data)


def pairing_history_to_dict(pairing_history: PairingHistory) -> Dict[str, Any]:
    return pairing_history.to_dict()


def pairing_history_from_dict(data: Dict[str, Any]) -> PairingHistory:
    return PairingHistory.from_dict(data)


def _reject_json_constant(value: str) -> None:
    raise TournamentDocumentError(f"JSON constant is not permitted: {value}")


def _validate_document_version(data: Mapping[str, Any]) -> None:
    version = data.get("__version__", CURRENT_DOCUMENT_VERSION)
    if not isinstance(version, int) or isinstance(version, bool) or version < 0:
        raise TournamentDocumentError("Document version must be a non-negative integer")
    if version > CURRENT_DOCUMENT_VERSION:
        raise TournamentDocumentError(
            f"Document version {version} is newer than supported version "
            f"{CURRENT_DOCUMENT_VERSION}"
        )


def _validate_config_data(data: Mapping[str, Any]) -> None:
    num_rounds = data.get("num_rounds")
    if (
        not isinstance(num_rounds, int)
        or isinstance(num_rounds, bool)
        or num_rounds < 1
    ):
        raise TournamentDocumentError(
            "Tournament num_rounds must be a positive integer"
        )

    if "name" in data and not isinstance(data["name"], str):
        raise TournamentDocumentError("Tournament name must be a string")
    if "pairing_system" in data and not isinstance(data["pairing_system"], str):
        raise TournamentDocumentError("Pairing system must be a string")
    if "tournament_mode" in data and not isinstance(data["tournament_mode"], str):
        raise TournamentDocumentError("Tournament mode must be a string")
    for field_name in (
        "fide_strict",
        "fide_strict_mode",
        "tournament_over",
        "use_experimental_dutch",
    ):
        if field_name in data and not isinstance(data[field_name], bool):
            raise TournamentDocumentError(f"{field_name} must be a boolean")
    if "tiebreak_order" in data:
        tiebreak_order = data["tiebreak_order"]
        if not isinstance(tiebreak_order, list) or not all(
            isinstance(item, str) for item in tiebreak_order
        ):
            raise TournamentDocumentError("Tiebreak order must be a list of strings")


def _load_players(player_data_list: List[Any]) -> List[Any]:
    players = []
    seen_ids: Set[str] = set()
    list_fields = (
        "color_history",
        "opponent_ids",
        "results",
        "outcome_types",
        "running_scores",
        "float_history",
        "match_history",
    )
    for index, raw_player in enumerate(player_data_list):
        if not isinstance(raw_player, Mapping):
            raise TournamentDocumentError(f"Player {index} must be an object")
        if not isinstance(raw_player.get("id"), str) or not raw_player["id"]:
            raise TournamentDocumentError(f"Player {index} must have a string ID")
        if not isinstance(raw_player.get("name"), str):
            raise TournamentDocumentError(f"Player {index} must have a name")
        player_id = raw_player["id"]
        if player_id in seen_ids:
            raise TournamentDocumentError(f"Duplicate player ID: {player_id}")
        for field_name in list_fields:
            if field_name in raw_player and not isinstance(
                raw_player[field_name], list
            ):
                raise TournamentDocumentError(
                    f"Player {player_id} field {field_name} must be a list"
                )
        if "score" in raw_player and not _is_finite_number(raw_player["score"]):
            raise TournamentDocumentError(f"Player {player_id} has an invalid score")
        if any(
            value is not None and not _is_valid_score(value)
            for value in raw_player.get("results", [])
        ):
            raise TournamentDocumentError(
                f"Player {player_id} has invalid result history"
            )
        if any(
            not _is_finite_number(value)
            for value in raw_player.get("running_scores", [])
        ):
            raise TournamentDocumentError(
                f"Player {player_id} has invalid running scores"
            )
        if any(
            value not in (None, "White", "Black")
            for value in raw_player.get("color_history", [])
        ):
            raise TournamentDocumentError(
                f"Player {player_id} has invalid color history"
            )
        if any(
            value is not None and value not in VALID_RESULT_OUTCOMES | {"bye"}
            for value in raw_player.get("outcome_types", [])
        ):
            raise TournamentDocumentError(
                f"Player {player_id} has invalid outcome history"
            )
        known_ids = {
            item.get("id") for item in player_data_list if isinstance(item, Mapping)
        }
        if any(
            value is not None and (not isinstance(value, str) or value not in known_ids)
            for value in raw_player.get("opponent_ids", [])
        ):
            raise TournamentDocumentError(
                f"Player {player_id} has unknown historical opponents"
            )
        if "is_active" in raw_player and not isinstance(raw_player["is_active"], bool):
            raise TournamentDocumentError(
                f"Player {player_id} is_active must be a boolean"
            )
        if "tiebreakers" in raw_player and not isinstance(
            raw_player["tiebreakers"], Mapping
        ):
            raise TournamentDocumentError(
                f"Player {player_id} tiebreakers must be an object"
            )

        try:
            player = create_player_from_dict(dict(raw_player))
        except Exception as error:
            raise TournamentDocumentError(
                f"Unable to load player {player_id}: {error}"
            ) from error
        if player.id != player_id:
            raise TournamentDocumentError(
                f"Player ID could not be restored: {player_id}"
            )
        players.append(player)
        seen_ids.add(player_id)
    return players


def _load_rounds(raw_rounds: Any, player_ids: Set[str]) -> List[RoundData]:
    if not isinstance(raw_rounds, list):
        raise TournamentDocumentError("Rounds must be a list")

    rounds: List[RoundData] = []
    for index, raw_round in enumerate(raw_rounds):
        if not isinstance(raw_round, Mapping):
            raise TournamentDocumentError(f"Round {index + 1} must be an object")
        round_number = raw_round.get("round_number", index + 1)
        if (
            not isinstance(round_number, int)
            or isinstance(round_number, bool)
            or round_number != index + 1
        ):
            raise TournamentDocumentError(
                f"Round numbers must be sequential, found {round_number!r}"
            )

        pairings = _load_round_pairings(
            raw_round.get("pairings", []), player_ids, round_number
        )
        pairing_orientations = set(pairings)
        expected_pairs = {frozenset(pairing) for pairing in pairings}
        bye_player_id = raw_round.get("bye_player_id", raw_round.get("bye_player"))
        if bye_player_id is not None:
            if not isinstance(bye_player_id, str) or bye_player_id not in player_ids:
                raise TournamentDocumentError(
                    f"Round {round_number} has an unknown bye player"
                )
            if bye_player_id in {player_id for pair in pairings for player_id in pair}:
                raise TournamentDocumentError(
                    f"Round {round_number} assigns its bye player to a game"
                )

        results = _load_round_results(
            raw_round.get("results", []),
            pairing_orientations,
            expected_pairs,
            player_ids,
            round_number,
        )
        result_pairs = {
            frozenset((result.white_id, result.black_id)) for result in results
        }
        pending_results = _load_round_results(
            raw_round.get("pending_results", []),
            pairing_orientations,
            expected_pairs,
            player_ids,
            round_number,
        )
        if result_pairs.intersection(
            frozenset((result.white_id, result.black_id)) for result in pending_results
        ):
            raise TournamentDocumentError(
                f"Round {round_number} contains both finalized and pending results "
                "for a pairing"
            )
        is_completed = raw_round.get("is_completed", False)
        if not isinstance(is_completed, bool):
            raise TournamentDocumentError(
                f"Round {round_number} is_completed must be a boolean"
            )
        if is_completed and (
            {frozenset((result.white_id, result.black_id)) for result in results}
            != expected_pairs
            or pending_results
        ):
            raise TournamentDocumentError(
                f"Completed round {round_number} does not contain a complete result set"
            )

        active_ids = raw_round.get("active_player_ids")
        if active_ids is not None and (
            not isinstance(active_ids, list)
            or any(
                not isinstance(key, str) or key not in player_ids for key in active_ids
            )
            or len(set(active_ids)) != len(active_ids)
        ):
            raise TournamentDocumentError(
                f"Round {round_number} has an invalid active roster"
            )
        scheduled = raw_round.get("scheduled_byes", {})
        assigned = {key for pair in pairings for key in pair}
        if bye_player_id:
            assigned.add(bye_player_id)
        if not isinstance(scheduled, Mapping):
            raise TournamentDocumentError("Scheduled byes must be an object")
        for kind, ids in scheduled.items():
            if kind not in {"half_point", "zero_point"} or not isinstance(ids, list):
                raise TournamentDocumentError("Invalid scheduled bye type")
            for key in ids:
                if not isinstance(key, str) or key not in player_ids or key in assigned:
                    raise TournamentDocumentError(
                        "Duplicate or unknown scheduled bye player"
                    )
                assigned.add(key)
        normalized_round = {
            "pairing_engine": raw_round.get("pairing_engine"),
            "scheduled_byes": raw_round.get("scheduled_byes", {}),
            "active_player_ids": active_ids,
            "round_number": round_number,
            "pairings": pairings,
            "bye_player_id": bye_player_id,
            "bye_type": raw_round.get("bye_type", "full"),
            "results": [result.to_dict() for result in results],
            "is_completed": is_completed,
            "pending_results": [result.to_dict() for result in pending_results],
        }
        rounds.append(round_data_from_dict(normalized_round))
    return rounds


def _load_round_pairings(
    raw_pairings: Any, player_ids: Set[str], round_number: int
) -> List[Tuple[str, str]]:
    if not isinstance(raw_pairings, (list, tuple)):
        raise TournamentDocumentError(f"Round {round_number} pairings must be a list")

    pairings: List[Tuple[str, str]] = []
    assigned_ids: Set[str] = set()
    seen_pairs: Set[frozenset] = set()
    for pairing in raw_pairings:
        if (
            not isinstance(pairing, (list, tuple))
            or len(pairing) != 2
            or not all(isinstance(player_id, str) for player_id in pairing)
        ):
            raise TournamentDocumentError(
                f"Round {round_number} contains an invalid pairing"
            )
        white_id, black_id = pairing
        pair = frozenset((white_id, black_id))
        if (
            white_id == black_id
            or white_id not in player_ids
            or black_id not in player_ids
            or pair in seen_pairs
            or white_id in assigned_ids
            or black_id in assigned_ids
        ):
            raise TournamentDocumentError(
                f"Round {round_number} contains duplicate, self, or unknown pairing IDs"
            )
        pairings.append((white_id, black_id))
        seen_pairs.add(pair)
        assigned_ids.update((white_id, black_id))
    return pairings


def _load_round_results(
    raw_results: Any,
    pairing_orientations: Set[Tuple[str, str]],
    expected_pairs: Set[frozenset],
    player_ids: Set[str],
    round_number: int,
) -> List[MatchResult]:
    if not isinstance(raw_results, list):
        raise TournamentDocumentError(f"Round {round_number} results must be a list")

    results: List[MatchResult] = []
    seen_pairs: Set[frozenset] = set()
    for raw_result in raw_results:
        if not isinstance(raw_result, Mapping):
            raise TournamentDocumentError(
                f"Round {round_number} contains an invalid result"
            )
        if not isinstance(raw_result.get("white_id"), str) or not isinstance(
            raw_result.get("black_id"), str
        ):
            raise TournamentDocumentError(
                f"Round {round_number} result IDs must be strings"
            )
        if not _is_finite_number(raw_result.get("white_score")):
            raise TournamentDocumentError(
                f"Round {round_number} result has an invalid white score"
            )
        if "black_score" in raw_result and not _is_finite_number(
            raw_result["black_score"]
        ):
            raise TournamentDocumentError(
                f"Round {round_number} result has an invalid black score"
            )
        if "outcome_type" in raw_result and not isinstance(
            raw_result["outcome_type"], str
        ):
            raise TournamentDocumentError(
                f"Round {round_number} result has an invalid outcome"
            )
        try:
            result = MatchResult.from_dict(dict(raw_result))
        except (KeyError, TypeError, ValueError) as error:
            raise TournamentDocumentError(
                f"Round {round_number} contains an invalid result: {error}"
            ) from error
        pair = frozenset((result.white_id, result.black_id))
        if (
            not isinstance(result.white_id, str)
            or not isinstance(result.black_id, str)
            or result.white_id not in player_ids
            or result.black_id not in player_ids
            or (result.white_id, result.black_id) not in pairing_orientations
            or pair not in expected_pairs
            or pair in seen_pairs
            or not _valid_match_result(result)
        ):
            raise TournamentDocumentError(
                f"Round {round_number} contains a result that does not match its pairing"
            )
        results.append(result)
        seen_pairs.add(pair)
    return results


def _valid_match_result(result: MatchResult) -> bool:
    if result.outcome_type not in VALID_RESULT_OUTCOMES:
        return False
    if not _is_valid_score(result.white_score):
        return False
    if result.black_score_override is not None and not _is_valid_score(
        result.black_score_override
    ):
        return False
    if result.outcome_type == OUTCOME_DOUBLE_FORFEIT:
        return result.white_score == LOSS_SCORE and result.black_score == LOSS_SCORE
    if result.outcome_type in {OUTCOME_FORFEIT_WIN, OUTCOME_FORFEIT_LOSS}:
        if result.white_score not in {LOSS_SCORE, WIN_SCORE}:
            return False
    return math.isclose(
        result.white_score + result.black_score,
        WIN_SCORE,
        abs_tol=SCORE_TOLERANCE,
    )


def _is_valid_score(value: Any) -> bool:
    return _is_finite_number(value) and any(
        math.isclose(float(value), valid_score, abs_tol=SCORE_TOLERANCE)
        for valid_score in VALID_RESULT_SCORES
    )


def _is_finite_number(value: Any) -> bool:
    return (
        isinstance(value, Real)
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _load_manual_adjustments(
    data: Mapping[str, Any], round_count: int
) -> Dict[int, Dict[str, Any]]:
    history_data = data.get("pairing_history")
    if history_data is not None:
        if not isinstance(history_data, Mapping):
            raise TournamentDocumentError("Pairing history must be an object")
        _validate_previous_matches(history_data.get("previous_matches", []))
        raw_adjustments = history_data.get("manual_adjustments", {})
    else:
        _validate_previous_matches(data.get("previous_matches", []))
        raw_adjustments = data.get("manual_pairings", {})

    if not isinstance(raw_adjustments, Mapping):
        raise TournamentDocumentError("Manual pairing adjustments must be an object")
    adjustments: Dict[int, Dict[str, Any]] = {}
    for raw_key, value in raw_adjustments.items():
        try:
            key = int(raw_key)
        except (TypeError, ValueError) as error:
            raise TournamentDocumentError(
                f"Invalid manual pairing round: {raw_key!r}"
            ) from error
        if key < 0 or key > round_count:
            continue
        if not isinstance(value, Mapping):
            raise TournamentDocumentError(
                f"Manual pairing adjustment {raw_key!r} must be an object"
            )
        adjustments[key] = dict(value)
    return adjustments


def _validate_previous_matches(raw_matches: Any) -> None:
    if not isinstance(raw_matches, list):
        raise TournamentDocumentError("Previous matches must be a list")
    for pair in raw_matches:
        if (
            not isinstance(pair, (list, tuple))
            or len(pair) != 2
            or not all(isinstance(player_id, str) for player_id in pair)
            or pair[0] == pair[1]
        ):
            raise TournamentDocumentError("Previous matches contain an invalid pair")


def _iter_player_dicts(players: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(players, dict):
        return players.values()
    if isinstance(players, list):
        return players
    raise TournamentDocumentError("Players must be a list or object")


def _legacy_rounds_from_dict(data: Mapping[str, Any]) -> List[RoundData]:
    pairings_by_round = data.get("rounds_pairings_ids", [])
    byes_by_round = data.get("rounds_byes_ids", [])
    if not isinstance(pairings_by_round, list):
        raise TournamentDocumentError("Legacy round pairings must be a list")
    if not isinstance(byes_by_round, list):
        raise TournamentDocumentError("Legacy byes must be a list")
    rounds: List[RoundData] = []

    for index, pairings in enumerate(pairings_by_round):
        if not isinstance(pairings, list):
            raise TournamentDocumentError("Legacy round pairings must be lists")
        for pairing in pairings:
            if not isinstance(pairing, (list, tuple)) or len(pairing) != 2:
                raise TournamentDocumentError(
                    "Legacy round pairings must contain two player IDs"
                )
        rounds.append(
            RoundData(
                round_number=index + 1,
                pairings=[tuple(pairing) for pairing in pairings],
                bye_player_id=(
                    byes_by_round[index] if index < len(byes_by_round) else None
                ),
            )
        )

    return rounds
